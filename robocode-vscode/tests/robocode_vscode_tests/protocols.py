from robocode_vscode.protocols import ListWorkspacesActionResultDict, ActionResultDict
from typing import Protocol
from robocode_ls_core.protocols import ILanguageServerClient


class IRobocodeLanguageServerClient(ILanguageServerClient, Protocol):
    def cloud_list_workspaces(
        self, refresh=False, packages=True
    ) -> ListWorkspacesActionResultDict:
        pass

    def upload_to_existing_activity(
        self, workspace_id: str, package_id: str, directory: str
    ) -> ActionResultDict:
        pass

    def upload_to_new_activity(
        self, workspace_id: str, package_name: str, directory: str
    ) -> ActionResultDict:
        pass
