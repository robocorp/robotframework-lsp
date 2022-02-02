from robocorp_ls_core.robotframework_log import get_logger
from typing import Any

log = get_logger(__name__)


class _RegisteredCommand(object):
    def __init__(self, command_name, expected_return_cls):
        self.command_name = command_name
        self.expected_return_type = expected_return_cls
        self.func = None
        self.attr_in_language_server = None


class _CommandDispatcher(object):
    def __init__(self):
        self._command_name_to_registered_command = {}

    def __call__(self, command_name, expected_return_cls=None):
        """
        :param expected_return_type:
            If None, the return type is not checked.
        """
        if isinstance(command_name, str):
            self._curr_registered_command = _RegisteredCommand(
                command_name, expected_return_cls
            )
            return self
        else:
            self._curr_registered_command.func = command_name
            self._command_name_to_registered_command[
                self._curr_registered_command.command_name
            ] = self._curr_registered_command
            return self._curr_registered_command.func

    def dispatch(self, language_server, command_name, arguments) -> Any:
        try:
            registered_command = self._command_name_to_registered_command[command_name]
            func = registered_command.func
            attr_in_language_server = registered_command.attr_in_language_server
            target = language_server
            if attr_in_language_server:
                target = getattr(language_server, attr_in_language_server)

            if registered_command.expected_return_type is None:
                return func(target, *arguments)
            else:
                ret = func(target, *arguments)
                assert isinstance(ret, registered_command.expected_return_type)
                return ret

        except Exception as e:
            error_msg = f"Error in command: {command_name} with args: {arguments}.\n{e}"
            log.exception(error_msg)
            return {"success": False, "message": error_msg, "result": None}

    def register_sub_command_dispatcher(self, sub_dispatcher):
        self._command_name_to_registered_command.update(
            sub_dispatcher._command_name_to_registered_command
        )


class _SubCommandDispatcher(object):
    def __init__(self, attr_in_language_server):
        self._command_name_to_registered_command = {}
        self.attr_in_language_server = attr_in_language_server

    def __call__(self, command_name, expected_return_cls=None):
        """
        :param expected_return_type:
            If None, the return type is not checked.
        """
        if isinstance(command_name, str):
            self._curr_registered_command = _RegisteredCommand(
                command_name, expected_return_cls
            )
            return self
        else:
            self._curr_registered_command.func = command_name
            self._curr_registered_command.attr_in_language_server = (
                self.attr_in_language_server
            )
            self._command_name_to_registered_command[
                self._curr_registered_command.command_name
            ] = self._curr_registered_command
            return self._curr_registered_command.func
