from concurrent import futures
from functools import partial
import itertools
from typing import Dict, Union

from robocorp_ls_core.protocols import (
    IConfig,
    ActionResultDict,
    ActionResult,
    Sentinel,
    IEndPoint,
    IFuture,
)
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.pluginmanager import PluginManager

log = get_logger(__name__)


class _RfInfo:
    def __init__(
        self,
        rf_interpreter_server_manager,
        commands_thread_pool: futures.ThreadPoolExecutor,
        ls_thread_pool: futures.ThreadPoolExecutor,
    ):
        from robotframework_interactive.server.rf_interpreter_server_manager import (
            RfInterpreterServerManager,
        )

        self.interpreter: RfInterpreterServerManager = rf_interpreter_server_manager
        self.commands_thread_pool = commands_thread_pool
        self.ls_thread_pool = ls_thread_pool


class _RfInterpretersManager:
    def __init__(
        self,
        endpoint: IEndPoint,
        pm: PluginManager,
        get_workspace_root_path=lambda: None,
    ):
        self._interpreter_id_to_rf_info: Dict[int, _RfInfo] = {}
        self._next_interpreter_id = partial(next, itertools.count(0))
        self._endpoint = endpoint
        self._pm = pm
        self._get_workspace_root_path = get_workspace_root_path

    def interpreter_start(
        self, arguments, config: IConfig
    ) -> Union[IFuture[ActionResultDict], ActionResultDict]:

        if not arguments:
            return ActionResult(
                False, message="Expected arguments ([{'uri': <uri>}])"
            ).as_dict()
        if not isinstance(arguments, (list, tuple)):
            return ActionResult(
                False, message=f"Arguments should be a Tuple[Dict]. Found: {arguments}"
            ).as_dict()

        args: dict = arguments[0]
        uri = args.get("uri", Sentinel.SENTINEL)
        if uri is Sentinel.SENTINEL:
            return ActionResult(
                False, message=f"Did not find 'uri' in {args}"
            ).as_dict()

        if not uri.endswith(".robot"):
            # We can't leave the URI as a .resource because then the parsing
            # we'd use is the one related to .resources (which can't have
            # tests) and then we wouldn't be able to create our current test
            # to be started in the interactive console.
            import os

            uri = os.path.splitext(uri)[0] + ".robot"

        # Thread pool with 1 worker (so, we're mostly sequentializing the
        # work to be done to another thread).
        commands_thread_pool = futures.ThreadPoolExecutor(max_workers=1)

        def run():
            from robotframework_ls import import_rf_interactive
            from robotframework_ls.config_extension import (
                apply_interpreter_info_to_config,
            )
            from robocorp_ls_core.ep_resolve_interpreter import EPResolveInterpreter
            from robocorp_ls_core import uris
            from robotframework_ls.impl.robot_lsp_constants import (
                OPTION_ROBOT_PYTHON_ENV,
            )

            import_rf_interactive()

            from robocorp_ls_core.options import Setup

            try:
                from robotframework_interactive.server.rf_interpreter_server_manager import (
                    RfInterpreterServerManager,
                )

                interpreter_id = self._next_interpreter_id()

                def on_interpreter_message(interpreter_message: dict):
                    """
                    :param interpreter_message:
                    Something as:
                    {
                        "jsonrpc": "2.0",
                        "method": "interpreter/output",
                        "params": {
                            "output": "Some output\n",
                            "category": "stdout",
                        },
                    }
                    """

                    params = interpreter_message["params"]
                    params["interpreter_id"] = interpreter_id
                    self._endpoint.notify(interpreter_message["method"], params)

                rf_interpreter_server_manager = RfInterpreterServerManager(
                    verbose=Setup.options.verbose,
                    base_log_file=Setup.options.log_file,
                    on_interpreter_message=on_interpreter_message,
                    uri=uri,
                )
                fs_path = uris.to_fs_path(uri)
                rf_interpreter_server_manager.config = config
                rf_config = rf_interpreter_server_manager.config

                # Just making sure that it has its own private copy before
                # mutating it...
                assert rf_config is not config

                info = {}
                for ep in self._pm.get_implementations(EPResolveInterpreter):
                    interpreter_info = ep.get_interpreter_info_for_doc_uri(uri)
                    if interpreter_info is not None:
                        target = str(interpreter_info.get_interpreter_id())
                        info["target"] = target
                        apply_interpreter_info_to_config(rf_config, interpreter_info)

                        existing_env = rf_config.get_setting(
                            OPTION_ROBOT_PYTHON_ENV, dict, {}
                        )

                        # Now, verify whether we have a
                        # 'robocorp.updateLaunchEnv', which is an additional
                        # hook that can be called to update the environment for
                        # launches (only available when we do have a custom
                        # interpreter set for it).
                        command_future = self._endpoint.request(
                            "$/executeWorkspaceCommand",
                            {
                                "command": "robocorp.updateLaunchEnv",
                                "arguments": {
                                    "targetRobot": target,
                                    "env": existing_env,
                                },
                            },
                        )
                        try:
                            new_env = command_future.result()
                            if new_env == "cancelled":
                                return ActionResult(
                                    False, message="Launch cancelled"
                                ).as_dict()
                        except:
                            log.exception(
                                "Unable to execute workspace command from the extension."
                            )
                        else:
                            if new_env:
                                if isinstance(new_env, dict):
                                    rf_config.update_override_settings(
                                        {OPTION_ROBOT_PYTHON_ENV: new_env}
                                    )
                                else:
                                    log.critical(
                                        "Expected robocorp.updateLaunchEnv to return a dict. Returned: %s (%s)",
                                        new_env,
                                        type(new_env),
                                    )

                        break

                info["path"] = str(fs_path)
                import json

                on_interpreter_message(
                    {
                        "jsonrpc": "2.0",
                        "method": "interpreter/output",
                        "params": {"output": json.dumps(info), "category": "json_info"},
                    }
                )
                rf_interpreter_server_manager.interpreter_start(
                    uri, workspace_root_path=self._get_workspace_root_path()
                )
                ls_thread_pool = futures.ThreadPoolExecutor(max_workers=2)
                self._interpreter_id_to_rf_info[interpreter_id] = _RfInfo(
                    rf_interpreter_server_manager, commands_thread_pool, ls_thread_pool
                )

            except Exception as e:
                log.exception("Error starting interpreter.")
                return ActionResult(False, message=str(e)).as_dict()
            else:
                return ActionResult(
                    True, result={"interpreter_id": interpreter_id}
                ).as_dict()

        return commands_thread_pool.submit(run)

    def get_interpreter_from_arguments(
        self, arguments
    ) -> Union[_RfInfo, ActionResultDict]:
        from robotframework_ls import import_rf_interactive

        import_rf_interactive()

        if not arguments:
            return ActionResult(
                False, message="Expected arguments ([{'interpreter_id': <id>}])"
            ).as_dict()
        if not isinstance(arguments, (list, tuple)):
            return ActionResult(
                False, message=f"Arguments should be a Tuple[Dict]. Found: {arguments}"
            ).as_dict()

        args: dict = arguments[0]
        interpreter_id = args.get("interpreter_id", Sentinel.SENTINEL)
        if interpreter_id is Sentinel.SENTINEL:
            return ActionResult(
                False, message=f"Did not find 'interpreter_id' in {args}"
            ).as_dict()

        rf_info = self._interpreter_id_to_rf_info.get(interpreter_id)
        if rf_info is None:
            return ActionResult(
                False, message=f"Did not find interpreter with id: {interpreter_id}"
            ).as_dict()
        return rf_info

    def interpreter_evaluate(
        self, arguments
    ) -> Union[IFuture[ActionResultDict], ActionResultDict]:
        from robotframework_ls import import_rf_interactive

        import_rf_interactive()

        from robotframework_interactive.server.rf_interpreter_server_manager import (
            RfInterpreterServerManager,
        )

        rf_info_or_dict_error: Union[
            _RfInfo, ActionResultDict
        ] = self.get_interpreter_from_arguments(arguments)
        if isinstance(rf_info_or_dict_error, dict):
            return rf_info_or_dict_error

        interpreter: RfInterpreterServerManager = rf_info_or_dict_error.interpreter
        args: dict = arguments[0]
        code = args.get("code", Sentinel.SENTINEL)
        if code is Sentinel.SENTINEL:
            return ActionResult(
                False, message=f"Did not find 'code' in {args}"
            ).as_dict()

        if interpreter.waiting_input:
            return interpreter.interpreter_evaluate(code)

        else:

            def run():
                return interpreter.interpreter_evaluate(code)

            return rf_info_or_dict_error.commands_thread_pool.submit(run)

    def interpreter_stop(
        self, arguments
    ) -> Union[IFuture[ActionResultDict], ActionResultDict]:
        from robotframework_ls import import_rf_interactive

        import_rf_interactive()

        rf_info_or_dict_error: Union[
            _RfInfo, ActionResultDict
        ] = self.get_interpreter_from_arguments(arguments)
        if isinstance(rf_info_or_dict_error, dict):
            return rf_info_or_dict_error

        rf_info: _RfInfo = rf_info_or_dict_error

        def run():
            try:
                return rf_info.interpreter.interpreter_stop()
            finally:
                try:
                    rf_info.commands_thread_pool.shutdown(wait=False)
                except:
                    log.exception("Error shutting down commands thread pool.")
                try:
                    rf_info.ls_thread_pool.shutdown(wait=False)
                except:
                    log.exception("Error shutting down ls thread pool.")

        return rf_info_or_dict_error.commands_thread_pool.submit(run)


def _handle_semantic_tokens(
    language_server_impl, rf_interpreters_manager: _RfInterpretersManager, arguments
):
    # When the user is entering text in the interpreter, the text
    # may not be the full text or it may be based on the text previously
    # entered, so, we need to ask the interpreter to compute the full
    # text so that we can get the semantic tokens based on the full
    # text that'll actually be evaluated.

    rf_info_or_dict_error: Union[
        _RfInfo, ActionResultDict
    ] = rf_interpreters_manager.get_interpreter_from_arguments(arguments)
    if isinstance(rf_info_or_dict_error, dict):
        msg = rf_info_or_dict_error.get("message")
        if msg:
            log.info(msg)
        return {"resultId": None, "data": []}

    from robotframework_interactive.server.rf_interpreter_server_manager import (
        RfInterpreterServerManager,
    )

    interpreter: RfInterpreterServerManager = rf_info_or_dict_error.interpreter
    uri = interpreter.uri

    api = language_server_impl._server_manager.get_others_api_client(uri)
    if api is None:
        log.info(
            "Unable to get api client when computing semantic tokens (for interactive usage)."
        )
        return {"resultId": None, "data": []}

    if not arguments or not isinstance(arguments, (list, tuple)) or len(arguments) != 1:
        log.info(f"Expected arguments to be a list of size 1. Found: {arguments}")
        return {"resultId": None, "data": []}

    def run():
        try:
            args: dict = arguments[0]
            code = args.get("code", Sentinel.SENTINEL)
            if code is Sentinel.SENTINEL:
                log.info(f"Did not find 'code' in {args}")
                return {"resultId": None, "data": []}

            evaluate_text_result = (
                rf_info_or_dict_error.interpreter.interpreter_compute_evaluate_text(
                    code
                )
            )
            if not evaluate_text_result["success"]:
                log.info(
                    "Unable to get code to evaluate semantic tokens (for interactive usage)."
                )
                return {"resultId": None, "data": []}
            else:
                code = evaluate_text_result["result"]

                return language_server_impl._threaded_api_request_no_doc(
                    api,
                    "request_semantic_tokens_from_code_full",
                    prefix=code["prefix"],
                    full_code=code["full_code"],
                    indent=code["indent"],
                    uri=uri,
                    monitor=None,
                )
        except:
            log.exception(f"Error computing semantic tokens for arguments: {arguments}")
            return {"resultId": None, "data": []}

    return rf_info_or_dict_error.ls_thread_pool.submit(run)


def _handle_completions(language_server_impl, rf_interpreters_manager, arguments):
    rf_info_or_dict_error: Union[
        _RfInfo, ActionResultDict
    ] = rf_interpreters_manager.get_interpreter_from_arguments(arguments)
    if isinstance(rf_info_or_dict_error, dict):
        msg = rf_info_or_dict_error.get("message")
        if msg:
            log.info(msg)
        return {"suggestions": []}

    from robotframework_interactive.server.rf_interpreter_server_manager import (
        RfInterpreterServerManager,
    )

    interpreter: RfInterpreterServerManager = rf_info_or_dict_error.interpreter
    uri = interpreter.uri

    api = language_server_impl._server_manager.get_regular_rf_api_client(uri)
    if api is None:
        log.info(
            "Unable to get api client when computing completions (for interactive usage)."
        )
        return {"suggestions": []}

    if not arguments or not isinstance(arguments, (list, tuple)) or len(arguments) != 1:
        log.info(f"Expected arguments to be a list of size 1. Found: {arguments}")
        return {"suggestions": []}

    def run():

        try:
            args: dict = arguments[0]
            code = args.get("code", Sentinel.SENTINEL)
            if code is Sentinel.SENTINEL:
                log.info(f"Did not find 'code' in {args}")
                return {"suggestions": []}

            position = args.get("position", Sentinel.SENTINEL)
            if position is Sentinel.SENTINEL:
                log.info(f"Did not find 'position' in {args}")
                return {"suggestions": []}

            # context = args.get("context", Sentinel.SENTINEL)
            # if context is Sentinel.SENTINEL:
            #     pass

            evaluate_text_result = interpreter.interpreter_compute_evaluate_text(
                code, "completions"
            )
            if not evaluate_text_result["success"]:
                log.info(
                    "Unable to get code to evaluate completions (for interactive usage)."
                )
                return {"suggestions": []}
            else:
                code = evaluate_text_result["result"]

                return language_server_impl._threaded_api_request_no_doc(
                    api,
                    "request_monaco_completions_from_code",
                    prefix=code["prefix"],
                    full_code=code["full_code"],
                    indent=code["indent"],
                    uri=uri,
                    position=position,
                    monitor=None,
                )
        except:
            log.exception(f"Error computing completions for arguments: {arguments}")
            return {"suggestions": []}

    return rf_info_or_dict_error.ls_thread_pool.submit(run)


def _handle_resolve_completion(
    language_server_impl, rf_interpreters_manager, arguments
):
    rf_info_or_dict_error: Union[
        _RfInfo, ActionResultDict
    ] = rf_interpreters_manager.get_interpreter_from_arguments(arguments)
    if isinstance(rf_info_or_dict_error, dict):
        msg = rf_info_or_dict_error.get("message")
        if msg:
            log.info(msg)
        return None

    from robotframework_interactive.server.rf_interpreter_server_manager import (
        RfInterpreterServerManager,
    )

    interpreter: RfInterpreterServerManager = rf_info_or_dict_error.interpreter
    uri = interpreter.uri

    api = language_server_impl._server_manager.get_regular_rf_api_client(uri)
    if api is None:
        log.info(
            "Unable to get api client when resolving completion (for interactive usage)."
        )
        return None

    if not arguments or not isinstance(arguments, (list, tuple)) or len(arguments) != 1:
        log.info(f"Expected arguments to be a list of size 1. Found: {arguments}")
        return None

    def run():

        try:
            args: dict = arguments[0]
            completion_item = args.get("completionItem", Sentinel.SENTINEL)
            if completion_item is Sentinel.SENTINEL:
                log.info(f"Did not find 'completionItem' in {args}")
                return None

            return language_server_impl._threaded_api_request_no_doc(
                api,
                "request_monaco_resolve_completion",
                completion_item=completion_item,
                monitor=None,
            )
        except:
            log.exception(f"Error computing completions for arguments: {arguments}")
            return {"suggestions": []}

    return rf_info_or_dict_error.ls_thread_pool.submit(run)


def execute_command(
    command,
    language_server_impl,
    rf_interpreters_manager: _RfInterpretersManager,
    arguments,
):
    from robotframework_ls.commands import (
        ROBOT_INTERNAL_RFINTERACTIVE_START,
        ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE,
        ROBOT_INTERNAL_RFINTERACTIVE_STOP,
        ROBOT_INTERNAL_RFINTERACTIVE_SEMANTIC_TOKENS,
        ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS,
        ROBOT_INTERNAL_RFINTERACTIVE_RESOLVE_COMPLETION,
    )

    if command == ROBOT_INTERNAL_RFINTERACTIVE_START:
        return rf_interpreters_manager.interpreter_start(
            arguments, language_server_impl.config
        )

    elif command == ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE:
        return rf_interpreters_manager.interpreter_evaluate(arguments)

    elif command == ROBOT_INTERNAL_RFINTERACTIVE_STOP:
        return rf_interpreters_manager.interpreter_stop(arguments)

    elif command == ROBOT_INTERNAL_RFINTERACTIVE_SEMANTIC_TOKENS:
        return _handle_semantic_tokens(
            language_server_impl, rf_interpreters_manager, arguments
        )

    elif command == ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS:
        return _handle_completions(
            language_server_impl, rf_interpreters_manager, arguments
        )

    elif command == ROBOT_INTERNAL_RFINTERACTIVE_RESOLVE_COMPLETION:
        return _handle_resolve_completion(
            language_server_impl, rf_interpreters_manager, arguments
        )
