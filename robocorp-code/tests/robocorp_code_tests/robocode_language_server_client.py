from robocorp_ls_core.unittest_tools.language_server_client import LanguageServerClient
from robocorp_code.protocols import (
    ListWorkspacesActionResultDict,
    UploadNewActivityParamsDict,
    UploadActivityParamsDict,
    ActionResultDict,
)
from robocorp_ls_core.basic import implements
from robocorp_code_tests.protocols import IRobocorpLanguageServerClient


class RobocorpLanguageServerClient(LanguageServerClient):
    @implements(IRobocorpLanguageServerClient.cloud_list_workspaces)
    def cloud_list_workspaces(
        self, refresh=False, packages=True
    ) -> ListWorkspacesActionResultDict:
        from robocorp_code import commands

        result = self.execute_command(
            commands.ROBOCORP_CLOUD_LIST_WORKSPACES_INTERNAL,
            [{"refresh": refresh, "packages": packages}],
        )["result"]
        return result

    @implements(IRobocorpLanguageServerClient.upload_to_existing_activity)
    def upload_to_existing_activity(
        self, workspace_id: str, package_id: str, directory: str
    ) -> ActionResultDict:
        from robocorp_code import commands

        params: UploadActivityParamsDict = {
            "workspaceId": workspace_id,
            "packageId": package_id,
            "directory": directory,
        }
        result = self.execute_command(
            commands.ROBOCORP_UPLOAD_TO_EXISTING_ACTIVITY_INTERNAL, [params]
        )["result"]
        return result

    @implements(IRobocorpLanguageServerClient.upload_to_new_activity)
    def upload_to_new_activity(
        self, workspace_id: str, package_name: str, directory: str
    ) -> ActionResultDict:
        from robocorp_code import commands

        paramsNew: UploadNewActivityParamsDict = {
            "workspaceId": workspace_id,
            "packageName": package_name,
            "directory": directory,
        }
        result = self.execute_command(
            commands.ROBOCORP_UPLOAD_TO_NEW_ACTIVITY_INTERNAL, [paramsNew]
        )["result"]
        return result

    def get_plugins_dir(self) -> str:
        from robocorp_code import commands

        result = self.execute_command(commands.ROBOCORP_GET_PLUGINS_DIR, [])["result"]
        return result

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IRobocorpLanguageServerClient = check_implements(self)
