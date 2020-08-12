from robocode_ls_core.unittest_tools.language_server_client import LanguageServerClient
from robocode_vscode.protocols import (
    ListWorkspacesActionResultDict,
    UploadNewActivityParamsDict,
    UploadActivityParamsDict,
    ActionResultDict,
)
from robocode_ls_core.basic import implements
from robocode_vscode_tests.protocols import IRobocodeLanguageServerClient


class RobocodeLanguageServerClient(LanguageServerClient):
    @implements(IRobocodeLanguageServerClient.cloud_list_workspaces)
    def cloud_list_workspaces(
        self, refresh=False, packages=True
    ) -> ListWorkspacesActionResultDict:
        from robocode_vscode import commands

        result = self.execute_command(
            commands.ROBOCODE_CLOUD_LIST_WORKSPACES_INTERNAL,
            [{"refresh": refresh, "packages": packages}],
        )["result"]
        return result

    @implements(IRobocodeLanguageServerClient.upload_to_existing_activity)
    def upload_to_existing_activity(
        self, workspace_id: str, package_id: str, directory: str
    ) -> ActionResultDict:
        from robocode_vscode import commands

        params: UploadActivityParamsDict = {
            "workspaceId": workspace_id,
            "packageId": package_id,
            "directory": directory,
        }
        result = self.execute_command(
            commands.ROBOCODE_UPLOAD_TO_EXISTING_ACTIVITY_INTERNAL, [params]
        )["result"]
        return result

    @implements(IRobocodeLanguageServerClient.upload_to_new_activity)
    def upload_to_new_activity(
        self, workspace_id: str, package_name: str, directory: str
    ) -> ActionResultDict:
        from robocode_vscode import commands

        paramsNew: UploadNewActivityParamsDict = {
            "workspaceId": workspace_id,
            "packageName": package_name,
            "directory": directory,
        }
        result = self.execute_command(
            commands.ROBOCODE_UPLOAD_TO_NEW_ACTIVITY_INTERNAL, [paramsNew]
        )["result"]
        return result

    def __typecheckself__(self) -> None:
        from robocode_ls_core.protocols import check_implements

        _: IRobocodeLanguageServerClient = check_implements(self)
