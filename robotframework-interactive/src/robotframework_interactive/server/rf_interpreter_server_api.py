from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.protocols import IConfig, ActionResultDict
from robocorp_ls_core.basic import overrides
from robocorp_ls_core.robotframework_log import get_logger
import threading
from robotframework_interactive.protocols import IMessage, IRobotFrameworkInterpreter
from robocorp_ls_core.options import DEFAULT_TIMEOUT, USE_TIMEOUTS, NO_TIMEOUT
from typing import Optional, Callable, Union, Dict, Any
import sys
import traceback
import json

log = get_logger(__name__)


class StopControwFlowException(Exception):
    pass


class RfInterpreterServerApi(PythonLanguageServer):
    def __init__(self, read_from, write_to) -> None:
        PythonLanguageServer.__init__(self, read_from, write_to)
        from queue import Queue

        self._interpreter_queue: "Queue[IMessage]" = Queue()
        self._interpreter_initialized = False
        self._interpreter_disposed = False
        self._interpreter: Optional[IRobotFrameworkInterpreter]
        self._finished_event = threading.Event()

    @overrides(PythonLanguageServer._create_config)
    def _create_config(self) -> IConfig:
        from robocorp_ls_core.config import Config

        return Config()

    def m_interpreter__start(
        self, uri: str, settings: Dict[str, Any], workspace_root_path: Optional[str]
    ) -> ActionResultDict:
        from robotframework_interactive.server.rf_interpreter_ls_config import (
            RfInterpreterRobotConfig,
        )

        if self._interpreter_initialized:
            return {
                "success": False,
                "message": "Interpreter already initialized",
                "result": None,
            }
        if self._interpreter_disposed:
            return {
                "success": False,
                "message": "Interpreter already disposed",
                "result": None,
            }

        try:
            from robotframework_interactive.interpreter import RobotFrameworkInterpreter

            config = RfInterpreterRobotConfig()
            config.update(settings)
            interpreter = RobotFrameworkInterpreter(config, workspace_root_path)
            self._interpreter = interpreter

            def on_output(msg: str, category: str):
                if not self._interpreter_disposed:
                    endpoint = self._lsp_messages.endpoint
                    endpoint.notify(
                        "interpreter/output", {"output": msg, "category": category}
                    )

            def on_stdout(msg: str):
                on_output(msg, "stdout")

            def on_stderr(msg: str):
                on_output(msg, "stderr")

            def on_before_read():
                if not self._interpreter_disposed:
                    endpoint = self._lsp_messages.endpoint
                    endpoint.notify("interpreter/beforeRead", {})

            def on_after_read():
                if not self._interpreter_disposed:
                    endpoint = self._lsp_messages.endpoint
                    endpoint.notify("interpreter/afterRead", {})

            def on_exception_handled(e):
                err_as_string = traceback.format_exc()
                try:
                    classname = e.__class__.__name__
                except:
                    classname = str(type(e))

                on_output(
                    json.dumps(
                        {
                            "description": str(e),
                            "traceback": err_as_string,
                            "type": classname,
                        }
                    ),
                    "exception",
                )
                return True

            interpreter.on_stdout.register(on_stdout)
            interpreter.on_stderr.register(on_stderr)
            interpreter.on_exception_handled.register(on_exception_handled)
            interpreter.on_before_read.register(on_before_read)
            interpreter.on_after_read.register(on_after_read)

            started_main_loop_event = threading.Event()

            def run_on_thread():
                def on_main_loop(interpreter: IRobotFrameworkInterpreter):
                    import robot

                    info = {
                        "sys.version": sys.version,
                        "sys.executable": sys.executable,
                        "robot.version": robot.get_version(),
                        "initialization.finished": True,
                    }
                    on_output(json.dumps(info), "json_info")

                    started_main_loop_event.set()

                    # Ok, we'll be stopped at this point receiving events and
                    # processing them.
                    self._interpreter_initialized = True
                    while True:
                        msg: IMessage = self._interpreter_queue.get()
                        try:
                            msg(interpreter)
                        except StopControwFlowException as e:
                            break

                        except Exception as e:
                            log.exception("Error evaluating: %s", msg)
                            msg.action_result_dict = {
                                "success": False,
                                "message": str(e),
                                "result": None,
                            }
                        finally:
                            msg.event.set()

                try:
                    interpreter.initialize(on_main_loop)
                finally:
                    self._finished_event.set()
                    self._interpreter = None

            t = threading.Thread(target=run_on_thread)
            t.start()
            assert started_main_loop_event.wait(
                DEFAULT_TIMEOUT if USE_TIMEOUTS else None
            )

            # Ok, at this point it's initialized.

            return {"success": True, "message": None, "result": True}
        except Exception as e:
            log.exception()
            return {"success": False, "message": str(e), "result": None}

    def m_interpreter__evaluate(
        self, code: str
    ) -> Union[Callable[[], ActionResultDict], ActionResultDict]:
        if not self._interpreter_initialized:
            return {
                "success": False,
                "message": "Interpreter still not initialized.",
                "result": None,
            }
        if self._interpreter_disposed:
            return {
                "success": False,
                "message": "Interpreter already disposed",
                "result": None,
            }

        evaluate = _Evaluate(code)
        self._interpreter_queue.put(evaluate)

        def func():
            evaluate.event.wait()
            return evaluate.action_result_dict

        return func

    def m_interpreter__compute_evaluate_text(
        self, code: str, target_type: str
    ) -> ActionResultDict:
        """
        :param target_type:
            'evaluate': means that the target is an evaluation with the given code.
                This implies that the current code must be changed to make sense
                in the given context.

            'completions': means that the target is a code-completion
                This implies that the current code must be changed to include
                all previous evaluation so that the code-completion contains
                the full information up to the current point.
        """
        if not self._interpreter_initialized:
            return {
                "success": False,
                "message": "Interpreter still not initialized.",
                "result": None,
            }
        if self._interpreter_disposed:
            return {
                "success": False,
                "message": "Interpreter already disposed",
                "result": None,
            }

        interpreter = self._interpreter
        if not interpreter:
            return {"success": False, "message": "Interpreter is None", "result": None}

        evaluate_text = interpreter.compute_evaluate_text(code, target_type=target_type)
        return {"success": True, "message": None, "result": evaluate_text}

    def m_interpreter__stop(self) -> ActionResultDict:
        stop = _Stop()
        if not self._interpreter_initialized or self._interpreter_disposed:
            return {
                "success": True,
                "message": None,  # Do nothing if not initialized nor disposed.
                "result": None,
            }
        self._interpreter_queue.put(stop)
        stop.event.wait()
        self._finished_event.wait(DEFAULT_TIMEOUT if USE_TIMEOUTS else NO_TIMEOUT)
        return stop.action_result_dict


class _Evaluate(object):
    def __init__(self, code: str):
        self.code = code
        self.event = threading.Event()
        self.action_result_dict: ActionResultDict = {
            "success": False,
            "message": "Code not evaluated.",
            "result": None,
        }

    def __call__(self, interpreter: IRobotFrameworkInterpreter):
        result = interpreter.evaluate(self.code)
        self.action_result_dict = result


class _Stop(object):
    def __init__(self) -> None:
        self.event = threading.Event()
        self.action_result_dict: ActionResultDict = {
            "success": False,
            "message": "Stop not executed.",
            "result": None,
        }

    def __call__(self, interpreter: IRobotFrameworkInterpreter) -> None:
        self.action_result_dict = {"success": True, "message": None, "result": None}
        raise StopControwFlowException()
