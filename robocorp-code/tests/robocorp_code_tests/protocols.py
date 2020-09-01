import sys

from robocorp_ls_core.protocols import ILanguageServerClient
from robocorp_code.protocols import ListWorkspacesActionResultDict, ActionResultDict


# Hack so that we don't break the runtime on versions prior to Python 3.8.
if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass


else:
    from typing import Protocol


class IRobocorpLanguageServerClient(ILanguageServerClient, Protocol):
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

    def get_plugins_dir(self) -> str:
        pass
