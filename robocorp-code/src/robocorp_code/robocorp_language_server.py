from robocorp_ls_core.basic import overrides
from robocorp_ls_core.python_ls import PythonLanguageServer, MAX_WORKERS
from robocorp_ls_core.robotframework_log import get_logger
from typing import List, Any, Optional, Dict
from robocorp_code import commands
from robocorp_code.protocols import (
    IRccWorkspace,
    IRccActivity,
    ActivityInfoDict,
    WorkspaceInfoDict,
    PackageInfoDict,
    ActionResultDict,
    UploadActivityParamsDict,
    UploadNewActivityParamsDict,
    CreateActivityParamsDict,
    CloudListWorkspaceDict,
    CloudLoginParamsDict,
    ListWorkspacesActionResultDict,
    PackageInfoInLRUDict,
)
import os
from robocorp_ls_core.protocols import IConfig


log = get_logger(__name__)

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]


class _RegisteredCommand(object):
    def __init__(self, command_name, expected_return_cls):
        self.command_name = command_name
        self.expected_return_type = expected_return_cls
        self.func = None


class _CommandDispatcher(object):
    def __init__(self):
        self._command_name_to_registered_command = {}

    def __call__(self, command_name, expected_return_cls=None):
        """
        :param expected_return_type:
            If None, the default expected is the ActionResultDict!
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

    def dispatch(self, language_server, command_name, arguments) -> ActionResultDict:
        try:
            registered_command = self._command_name_to_registered_command[command_name]
            func = registered_command.func

            if registered_command.expected_return_type is None:
                ret: ActionResultDict = func(language_server, *arguments)
                assert isinstance(ret, dict)
                assert "success" in ret
                return ret
            else:
                ret = func(language_server, *arguments)
                assert isinstance(ret, registered_command.expected_return_type)
                return ret

        except Exception as e:
            error_msg = f"Error in command: {command_name} with args: {arguments}.\n{e}"
            log.exception(error_msg)
            return {"success": False, "message": error_msg, "result": None}


command_dispatcher = _CommandDispatcher()


class RobocorpLanguageServer(PythonLanguageServer):

    CLOUD_LIST_WORKSPACE_CACHE_KEY = "CLOUD_LIST_WORKSPACE_CACHE"
    PACKAGE_ACCESS_LRU_CACHE_KEY = "PACKAGE_ACCESS_LRU_CACHE"

    def __init__(self, read_stream, write_stream, max_workers=MAX_WORKERS):
        from robocorp_code.rcc import Rcc
        from robocorp_ls_core.cache import DirCache

        user_home = os.getenv("ROBOCORP_CODE_USER_HOME", None)
        if user_home is None:
            user_home = os.path.expanduser("~")
        cache_dir = os.path.join(user_home, ".robocorp-code", ".cache")

        log.debug(f"Cache dir: {cache_dir}")

        self._dir_cache = DirCache(cache_dir)
        self._rcc = Rcc(self)
        PythonLanguageServer.__init__(
            self, read_stream, write_stream, max_workers=max_workers
        )

    @overrides(PythonLanguageServer._create_config)
    def _create_config(self) -> IConfig:
        from robocorp_code.robocorp_config import RobocorpConfig

        return RobocorpConfig()

    @overrides(PythonLanguageServer.capabilities)
    def capabilities(self):
        from robocorp_ls_core.lsp import TextDocumentSyncKind
        from robocorp_code.commands import ALL_SERVER_COMMANDS

        server_capabilities = {
            "codeActionProvider": False,
            # "codeLensProvider": {
            #     "resolveProvider": False,  # We may need to make this configurable
            # },
            "completionProvider": {
                "resolveProvider": False  # We know everything ahead of time
            },
            "documentFormattingProvider": False,
            "documentHighlightProvider": False,
            "documentRangeFormattingProvider": False,
            "documentSymbolProvider": False,
            "definitionProvider": True,
            "executeCommandProvider": {"commands": ALL_SERVER_COMMANDS},
            "hoverProvider": False,
            "referencesProvider": False,
            "renameProvider": False,
            "foldingRangeProvider": False,
            "textDocumentSync": {
                "change": TextDocumentSyncKind.INCREMENTAL,
                "save": {"includeText": False},
                "openClose": True,
            },
            "workspace": {
                "workspaceFolders": {"supported": True, "changeNotifications": True}
            },
        }
        log.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

    def m_workspace__execute_command(self, command=None, arguments=()) -> Any:
        return command_dispatcher.dispatch(self, command, arguments)

    @command_dispatcher(commands.ROBOCORP_IS_LOGIN_NEEDED_INTERNAL)
    def _is_login_needed_internal(self) -> ActionResultDict:
        from robocorp_ls_core.progress_report import progress_context

        with progress_context(
            self._endpoint, "Validating cloud credentials", self._dir_cache
        ):
            login_needed = not self._rcc.credentials_valid()
        return {"success": login_needed, "message": None, "result": login_needed}

    @command_dispatcher(commands.ROBOCORP_CLOUD_LOGIN_INTERNAL)
    def _cloud_login(self, params: CloudLoginParamsDict) -> ActionResultDict:
        from robocorp_ls_core.progress_report import progress_context

        # When new credentials are added we need to remove existing caches.
        self._dir_cache.discard(self.CLOUD_LIST_WORKSPACE_CACHE_KEY)

        credentials = params["credentials"]
        with progress_context(
            self._endpoint, "Adding cloud credentials", self._dir_cache
        ):
            result = self._rcc.add_credentials(credentials)
            if not result.success:
                return result.as_dict()

            result = self._rcc.credentials_valid()
        return {"success": result, "message": None, "result": result}

    def _get_sort_key_info(self):
        try:
            cache_lru_list: List[PackageInfoInLRUDict] = self._dir_cache.load(
                self.PACKAGE_ACCESS_LRU_CACHE_KEY, list
            )
        except KeyError:
            cache_lru_list = []
        DEFAULT_SORT_KEY = 10
        ws_id_and_pack_id_to_lru_index: Dict = {}
        for i, entry in enumerate(cache_lru_list):

            if i >= DEFAULT_SORT_KEY:
                break

            if isinstance(entry, dict):
                ws_id = entry.get("workspace_id")
                pack_id = entry.get("package_id")
                if ws_id is not None and pack_id is not None:
                    key = (ws_id, pack_id)
                    ws_id_and_pack_id_to_lru_index[key] = i
        return ws_id_and_pack_id_to_lru_index

    @command_dispatcher(commands.ROBOCORP_CLOUD_LIST_WORKSPACES_INTERNAL)
    def _cloud_list_workspaces(
        self, params: CloudListWorkspaceDict
    ) -> ListWorkspacesActionResultDict:
        from robocorp_ls_core.progress_report import progress_context

        DEFAULT_SORT_KEY = 10
        package_info: PackageInfoDict
        ws_dict: WorkspaceInfoDict

        ws_id_and_pack_id_to_lru_index = self._get_sort_key_info()

        if not params.get("refresh", True):
            try:
                cached: List[WorkspaceInfoDict] = self._dir_cache.load(
                    self.CLOUD_LIST_WORKSPACE_CACHE_KEY, list
                )
            except KeyError:
                pass
            else:
                # We need to update the sort key when it's gotten from the cache.
                try:
                    for ws_dict in cached:
                        for package_info in ws_dict["packages"]:
                            key = (package_info["workspaceId"], package_info["id"])
                            sort_key = "%05d%s" % (
                                ws_id_and_pack_id_to_lru_index.get(
                                    key, DEFAULT_SORT_KEY
                                ),
                                package_info["name"].lower(),
                            )

                            package_info["sortKey"] = sort_key
                    return {"success": True, "message": None, "result": cached}
                except Exception:
                    log.exception(
                        "Error computing new sort keys for cached entry. Refreshing and proceeding."
                    )

        with progress_context(
            self._endpoint, "Listing cloud workspaces", self._dir_cache
        ):
            ws: IRccWorkspace
            ret: List[WorkspaceInfoDict] = []
            result = self._rcc.cloud_list_workspaces()
            if not result.success:
                return result.as_dict()

            workspaces = result.result
            for ws in workspaces:
                packages: List[PackageInfoDict] = []

                activity_package: IRccActivity
                activities_result = self._rcc.cloud_list_workspace_activities(
                    ws.workspace_id
                )
                if not activities_result.success:
                    return activities_result.as_dict()

                workspace_activities = activities_result.result
                for activity_package in workspace_activities:

                    key = (ws.workspace_id, activity_package.activity_id)
                    sort_key = "%05d%s" % (
                        ws_id_and_pack_id_to_lru_index.get(key, DEFAULT_SORT_KEY),
                        activity_package.activity_name.lower(),
                    )

                    package_info = {
                        "name": activity_package.activity_name,
                        "id": activity_package.activity_id,
                        "sortKey": sort_key,
                        "workspaceId": ws.workspace_id,
                    }
                    packages.append(package_info)

                ws_dict = {
                    "workspaceName": ws.workspace_name,
                    "workspaceId": ws.workspace_id,
                    "packages": packages,
                }
                ret.append(ws_dict)

        if ret:  # Only store if we got something.
            self._dir_cache.store(self.CLOUD_LIST_WORKSPACE_CACHE_KEY, ret)
        return {"success": True, "message": None, "result": ret}

    @command_dispatcher(commands.ROBOCORP_CREATE_ACTIVITY_INTERNAL)
    def _create_activity(self, params: CreateActivityParamsDict) -> ActionResultDict:
        directory = params["directory"]
        template = params["template"]
        name = params["name"]

        return self._rcc.create_activity(
            template, os.path.join(directory, name)
        ).as_dict()

    @command_dispatcher(commands.ROBOCORP_LIST_ACTIVITY_TEMPLATES_INTERNAL)
    def _list_activity_templates(self, params=None) -> ActionResultDict:
        result = self._rcc.get_template_names()
        return result.as_dict()

    @command_dispatcher(commands.ROBOCORP_LOCAL_LIST_ACTIVITIES_INTERNAL)
    def _local_list_activities(self, params=None) -> ActionResultDict:
        from pathlib import Path

        ret: List[ActivityInfoDict] = []
        try:
            ws = self.workspace
            if ws:
                for folder_path in ws.get_folder_paths():
                    p = Path(folder_path)
                    if p.is_dir():
                        for sub in p.iterdir():
                            package_yaml = sub / "package.yaml"
                            if package_yaml.exists():
                                folder_info: ActivityInfoDict = {
                                    "directory": str(sub),
                                    "name": sub.name,
                                }
                                ret.append(folder_info)
            ret.sort(key=lambda dct: dct["name"])
        except Exception as e:
            log.exception("Error listing activities.")
            return dict(success=False, message=str(e), result=None)
        return dict(success=True, message=None, result=ret)

    def _validate_directory(self, directory) -> Optional[str]:
        if not os.path.exists(directory):
            return f"Expected: {directory} to exist."

        if not os.path.isdir(directory):
            return f"Expected: {directory} to be a directory."
        return None

    def _add_package_info_to_access_lru(self, workspace_id, package_id, directory):
        import time

        try:
            lst: List[PackageInfoInLRUDict] = self._dir_cache.load(
                self.PACKAGE_ACCESS_LRU_CACHE_KEY, list
            )
        except KeyError:
            lst = []

        new_lst: List[PackageInfoInLRUDict] = [
            {
                "workspace_id": workspace_id,
                "package_id": package_id,
                "directory": directory,
                "time": time.time(),
            }
        ]
        for i, entry in enumerate(lst):
            if isinstance(entry, dict):
                if (
                    entry.get("package_id") == package_id
                    and entry.get("workspace_id") == workspace_id
                ):
                    continue  # Skip this one (we moved it to the start of the LRU).
                new_lst.append(entry)

            if i == 5:
                break  # Max number of items in the LRU reached.

        self._dir_cache.store(self.PACKAGE_ACCESS_LRU_CACHE_KEY, new_lst)

    @command_dispatcher(commands.ROBOCORP_UPLOAD_TO_EXISTING_ACTIVITY_INTERNAL)
    def _upload_to_existing_activity(
        self, params: UploadActivityParamsDict
    ) -> ActionResultDict:
        from robocorp_ls_core.progress_report import progress_context

        directory = params["directory"]
        error_msg = self._validate_directory(directory)
        if error_msg:
            return {"success": False, "message": error_msg, "result": None}

        workspace_id = params["workspaceId"]
        package_id = params["packageId"]
        with progress_context(
            self._endpoint, "Uploading to existing activity package", self._dir_cache
        ):

            result = self._rcc.cloud_set_activity_contents(
                directory, workspace_id, package_id
            )
            self._add_package_info_to_access_lru(workspace_id, package_id, directory)

        return result.as_dict()

    @command_dispatcher(commands.ROBOCORP_UPLOAD_TO_NEW_ACTIVITY_INTERNAL)
    def _upload_to_new_activity(
        self, params: UploadNewActivityParamsDict
    ) -> ActionResultDict:
        from robocorp_ls_core.progress_report import progress_context

        directory = params["directory"]
        error_msg = self._validate_directory(directory)
        if error_msg:
            return {"success": False, "message": error_msg, "result": None}

        workspace_id = params["workspaceId"]
        package_name = params["packageName"]

        # When we upload to a new activity, clear the existing cache key.
        self._dir_cache.discard(self.CLOUD_LIST_WORKSPACE_CACHE_KEY)
        with progress_context(
            self._endpoint, "Uploading to new activity package", self._dir_cache
        ):
            new_activity_result = self._rcc.cloud_create_activity(
                workspace_id, package_name
            )
            if not new_activity_result.success:
                return new_activity_result.as_dict()

            package_id = new_activity_result.result
            if not package_id:
                return dict(
                    success=False,
                    message="Expected to have package id from creating new activity.",
                    result=None,
                )

            result = self._rcc.cloud_set_activity_contents(
                directory, workspace_id, package_id
            )
            self._add_package_info_to_access_lru(workspace_id, package_id, directory)
        return result.as_dict()

    @command_dispatcher(commands.ROBOCORP_GET_PLUGINS_DIR, str)
    def _get_plugins_dir(self, params=None) -> str:
        from pathlib import Path

        return str(Path(__file__).parent / "plugins")
