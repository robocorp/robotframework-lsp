from robocorp_ls_core.command_dispatcher import _SubCommandDispatcher
from robocorp_ls_core.protocols import ActionResultDict, IEndPoint
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code import commands
from robocorp_code.protocols import CloudLoginParamsDict, IRcc

log = get_logger(__name__)
login_command_dispatcher = _SubCommandDispatcher("_login")


class _Login(object):
    def __init__(
        self,
        dir_cache,
        endpoint: IEndPoint,
        base_command_dispatcher,
        rcc: IRcc,
        feedback,
        clear_caches_on_login_change,
    ):
        from robocorp_ls_core.cache import DirCache

        from robocorp_code._language_server_feedback import _Feedback

        self._dir_cache: DirCache = dir_cache
        self._endpoint = endpoint
        self._rcc = rcc
        self._feedback: _Feedback = feedback
        self._clear_caches_on_login_change = clear_caches_on_login_change

        base_command_dispatcher.register_sub_command_dispatcher(
            login_command_dispatcher
        )

    @login_command_dispatcher(commands.ROBOCORP_IS_LOGIN_NEEDED_INTERNAL)
    def _is_login_needed_internal(self) -> ActionResultDict:
        from robocorp_ls_core.progress_report import progress_context

        with progress_context(
            self._endpoint, "Validating Control Room credentials", self._dir_cache
        ):
            login_needed = not self._rcc.credentials_valid()
        return {"success": login_needed, "message": None, "result": login_needed}

    @login_command_dispatcher(commands.ROBOCORP_CLOUD_LOGIN_INTERNAL)
    def _cloud_login(self, params: CloudLoginParamsDict) -> ActionResultDict:
        from robocorp_ls_core.progress_report import progress_context

        self._feedback.metric("vscode.cloud.login")

        # When new credentials are added we need to remove existing caches.
        self._clear_caches_on_login_change()

        credentials = params["credentials"]
        with progress_context(
            self._endpoint, "Adding Control Room credentials", self._dir_cache
        ):
            action_result = self._rcc.add_credentials(credentials)
            self._endpoint.notify("$/linkedAccountChanged")
            if not action_result.success:
                return action_result.as_dict()

            result = self._rcc.credentials_valid()
        return {"success": result, "message": None, "result": result}

    @login_command_dispatcher(commands.ROBOCORP_CLOUD_LOGOUT_INTERNAL)
    def _cloud_logout(self) -> ActionResultDict:
        from robocorp_ls_core.progress_report import progress_context

        self._feedback.metric("vscode.cloud.logout")

        # When credentials are removed we need to remove existing caches.
        self._clear_caches_on_login_change()

        with progress_context(
            self._endpoint, "Removing Control Room credentials", self._dir_cache
        ):
            ret = self._rcc.remove_current_credentials().as_dict()
            self._endpoint.notify("$/linkedAccountChanged")
            return ret
