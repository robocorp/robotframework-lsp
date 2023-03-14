from robocorp_ls_core.protocols import IEndPoint, ActionResultDict
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_code import commands
from robocorp_ls_core.command_dispatcher import _SubCommandDispatcher
from robocorp_code.protocols import (
    IRcc,
    ProfileImportParamsDict,
    ProfileSwitchParamsDict,
    ProfileListResultTypedDict,
)

log = get_logger(__name__)
profile_command_dispatcher = _SubCommandDispatcher("_profile")


class _Profile(object):
    def __init__(
        self,
        endpoint: IEndPoint,
        base_command_dispatcher,
        rcc: IRcc,
        feedback,
    ):
        from robocorp_code._language_server_feedback import _Feedback

        self._endpoint = endpoint
        self._rcc = rcc
        self._feedback: _Feedback = feedback

        base_command_dispatcher.register_sub_command_dispatcher(
            profile_command_dispatcher
        )

    @profile_command_dispatcher(commands.ROBOCORP_PROFILE_IMPORT_INTERNAL)
    def _profile_import(self, params: ProfileImportParamsDict) -> ActionResultDict:
        from robocorp_ls_core.progress_report import progress_context
        from robocorp_ls_core import yaml_wrapper
        from robocorp_ls_core import uris

        self._feedback.metric("vscode.profile.import")

        profile_uri = params["profileUri"]
        with progress_context(self._endpoint, "Import profile", None):

            file_path = uris.to_fs_path(profile_uri)
            profile_name: str = ""
            description: str = ""
            try:
                with open(file_path, "r", encoding="utf-8") as stream:
                    contents = yaml_wrapper.load(stream)
                    profile_name = contents.get("name", "")
                    description = contents.get("description", "")
            except Exception as e:
                msg = f"Error loading: {file_path} as yaml: {e}."
                log.exception(msg)
                return {"success": False, "message": msg, "result": None}

            if not profile_name:
                return {
                    "success": False,
                    "message": "Profile 'name' not available in yaml.",
                    "result": None,
                }

            action_result = self._rcc.profile_import(file_path)
            if not action_result.success:
                return action_result.as_dict()

            result = {"name": profile_name, "description": description}
        return {"success": True, "message": None, "result": result}

    @profile_command_dispatcher(commands.ROBOCORP_PROFILE_SWITCH_INTERNAL)
    def _profile_switch(self, params: ProfileSwitchParamsDict) -> ActionResultDict:
        from robocorp_ls_core.progress_report import progress_context

        self._feedback.metric("vscode.profile.switch")

        profile_name = params["profileName"]
        with progress_context(self._endpoint, "Switch profile", None):

            if not profile_name:
                return {
                    "success": False,
                    "message": "Profile 'name' not available in yaml.",
                    "result": None,
                }

            action_result = self._rcc.profile_switch(profile_name)
            if not action_result.success:
                return action_result.as_dict()

            self._endpoint.notify("$/linkedAccountChanged")

            result = True
        return {"success": True, "message": None, "result": result}

    @profile_command_dispatcher(commands.ROBOCORP_PROFILE_LIST_INTERNAL)
    def _profile_list(self, *params) -> ActionResultDict:
        from robocorp_ls_core.protocols import ActionResult

        action_result: ActionResult[
            ProfileListResultTypedDict
        ] = self._rcc.profile_list()
        return action_result.as_dict()
