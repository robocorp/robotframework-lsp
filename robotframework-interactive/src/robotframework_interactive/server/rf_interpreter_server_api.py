from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.protocols import IConfig, ActionResultDict
from robocorp_ls_core.basic import overrides
from robocorp_ls_core.robotframework_log import get_logger
import threading
from robotframework_interactive.protocols import IMessage, IRobotFrameworkInterpreter
from robocorp_ls_core.options import DEFAULT_TIMEOUT, USE_TIMEOUTS, NO_TIMEOUT

log = get_logger(__name__)


class StopControwFlowException(Exception):
    pass


class RfInterpreterServerApi(PythonLanguageServer):
    def __init__(self, read_from, write_to):
        PythonLanguageServer.__init__(self, read_from, write_to)
        from queue import Queue

        self._interpreter_queue: "Queue[IMessage]" = Queue()
        self._interpreter_initialized = False
        self._interpreter_disposed = False
        self._finished_event = threading.Event()

    @overrides(PythonLanguageServer._create_config)
    def _create_config(self) -> IConfig:
        from robocorp_ls_core.config import Config

        return Config()

    def m_interpreter__start(self) -> ActionResultDict:
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

            interpreter = RobotFrameworkInterpreter()

            def on_stdout(msg: str):
                if not self._interpreter_disposed:
                    endpoint = self._lsp_messages.endpoint
                    endpoint.notify(
                        "interpreter/output", {"output": msg, "category": "stdout"}
                    )

            def on_stderr(msg: str):
                if not self._interpreter_disposed:
                    endpoint = self._lsp_messages.endpoint
                    endpoint.notify(
                        "interpreter/output", {"output": msg, "category": "stderr"}
                    )

            interpreter.on_stdout.register(on_stdout)
            interpreter.on_stderr.register(on_stderr)

            started_main_loop_event = threading.Event()

            def run_on_thread():
                def on_main_loop(interpreter: IRobotFrameworkInterpreter):
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
                            msg.processed_event.set()

                try:
                    interpreter.initialize(on_main_loop)
                finally:
                    self._finished_event.set()

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

    def m_interpreter__evaluate(self, code: str) -> ActionResultDict:
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
        evaluate.processed_event.wait()
        return evaluate.action_result_dict

    def m_interpreter__stop(self) -> ActionResultDict:
        stop = _Stop()
        if not self._interpreter_initialized or self._interpreter_disposed:
            return {
                "success": True,
                "message": None,  # Do nothing if not initialized nor disposed.
                "result": None,
            }
        self._interpreter_queue.put(stop)
        stop.processed_event.wait()
        self._finished_event.wait(DEFAULT_TIMEOUT if USE_TIMEOUTS else NO_TIMEOUT)
        return stop.action_result_dict


class _Evaluate(object):
    def __init__(self, code: str):
        self.code = code
        self.processed_event = threading.Event()
        self.action_result_dict = {
            "success": False,
            "message": "Code not evaluated.",
            "result": None,
        }

    def __call__(self, interpreter: IRobotFrameworkInterpreter):
        result = interpreter.evaluate(self.code)
        self.action_result_dict = {"success": True, "message": None, "result": result}


class _Stop(object):
    def __init__(self):
        self.processed_event = threading.Event()
        self.action_result_dict = {
            "success": False,
            "message": "Stop not executed.",
            "result": None,
        }

    def __call__(self, interpreter: IRobotFrameworkInterpreter):
        self.action_result_dict = {"success": True, "message": None, "result": None}
        raise StopControwFlowException()
