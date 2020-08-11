from robocode_ls_core.basic import overrides
from robocode_ls_core.python_ls import PythonLanguageServer, MAX_WORKERS
from robocode_ls_core.robotframework_log import get_logger
from typing import List, Any
from robocode_vscode import commands
from robocode_vscode.protocols import (
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
)


log = get_logger(__name__)


class _CommandDispatcher(object):
    def __init__(self):
        self._command_name_to_func = {}

    def __call__(self, command_name):
        if isinstance(command_name, str):
            self._curr_command_name = command_name
            return self
        else:
            func = command_name
            self._command_name_to_func[self._curr_command_name] = func
            return func

    def dispatch(self, language_server, command_name, arguments) -> ActionResultDict:
        try:
            ret: ActionResultDict = self._command_name_to_func[command_name](
                language_server, *arguments
            )
            assert isinstance(ret, dict)
            assert "success" in ret
            return ret
        except Exception as e:
            error_msg = f"Error in command: {command_name} with args: {arguments}.\n{e}"
            log.exception(error_msg)
            return {"success": False, "message": error_msg, "result": None}


command_dispatcher = _CommandDispatcher()


class RobocodeLanguageServer(PythonLanguageServer):

    CLOUD_LIST_WORKSPACE_CACHE_KEY = "CLOUD_LIST_WORKSPACE_CACHE"

    def __init__(self, read_stream, write_stream, max_workers=MAX_WORKERS):
        from robocode_vscode.rcc import Rcc
        from robocode_ls_core.cache import DirCache

        self._rcc = Rcc(self)
        self._dir_cache = DirCache(".robocode-vscode", "ROBOCODE_VSCODE_USER_HOME")
        PythonLanguageServer.__init__(
            self, read_stream, write_stream, max_workers=max_workers
        )

    @overrides(PythonLanguageServer.capabilities)
    def capabilities(self):
        from robocode_ls_core.lsp import TextDocumentSyncKind
        from robocode_vscode.commands import ALL_SERVER_COMMANDS

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

    @command_dispatcher(commands.ROBOCODE_IS_LOGIN_NEEDED_INTERNAL)
    def _is_login_needed_internal(self) -> ActionResultDict:
        from robocode_ls_core.progress_report import progress_context

        with progress_context(
            self._endpoint, "Validating cloud credentials", self._dir_cache
        ):
            login_needed = not self._rcc.credentials_valid()
        return {"success": login_needed, "message": None, "result": login_needed}

    @command_dispatcher(commands.ROBOCODE_CLOUD_LOGIN_INTERNAL)
    def _cloud_login(self, params: CloudLoginParamsDict) -> ActionResultDict:
        from robocode_ls_core.progress_report import progress_context

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

    @command_dispatcher(commands.ROBOCODE_CLOUD_LIST_WORKSPACES_INTERNAL)
    def _cloud_list_workspaces(
        self, params: CloudListWorkspaceDict
    ) -> ListWorkspacesActionResultDict:
        from robocode_ls_core.progress_report import progress_context

        if not params.get("refresh", True):
            try:
                cached = self._dir_cache.load(self.CLOUD_LIST_WORKSPACE_CACHE_KEY, list)
            except KeyError:
                pass
            else:
                return {"success": True, "message": None, "result": cached}

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
                    package_info: PackageInfoDict = {
                        "name": activity_package.activity_name,
                        "id": activity_package.activity_id,
                        "lastSelected": False,
                        "workspaceId": ws.workspace_id,
                    }
                    packages.append(package_info)

                ws_dict: WorkspaceInfoDict = {
                    "workspaceName": ws.workspace_name,
                    "workspaceId": ws.workspace_id,
                    "packages": packages,
                }
                ret.append(ws_dict)

        if ret:  # Only store if we got something.
            self._dir_cache.store(self.CLOUD_LIST_WORKSPACE_CACHE_KEY, ret)
        return {"success": True, "message": None, "result": ret}

    @command_dispatcher(commands.ROBOCODE_CREATE_ACTIVITY_INTERNAL)
    def _create_activity(self, params: CreateActivityParamsDict) -> ActionResultDict:
        import os.path

        directory = params["directory"]
        template = params["template"]
        name = params["name"]

        return self._rcc.create_activity(
            template, os.path.join(directory, name)
        ).as_dict()

    @command_dispatcher(commands.ROBOCODE_LIST_ACTIVITY_TEMPLATES_INTERNAL)
    def _list_activity_templates(self, params=None) -> ActionResultDict:
        result = self._rcc.get_template_names()
        return result.as_dict()

    @command_dispatcher(commands.ROBOCODE_LOCAL_LIST_ACTIVITIES_INTERNAL)
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

    @command_dispatcher(commands.ROBOCODE_UPLOAD_TO_EXISTING_ACTIVITY_INTERNAL)
    def _upload_to_existing_activity(
        self, params: UploadActivityParamsDict
    ) -> ActionResultDict:
        from robocode_ls_core.progress_report import progress_context

        directory = params["directory"]
        workspace_id = params["workspaceId"]
        package_id = params["packageId"]
        with progress_context(
            self._endpoint, "Uploading to existing activity package", self._dir_cache
        ):

            result = self._rcc.cloud_set_activity_contents(
                directory, workspace_id, package_id
            )
        return result.as_dict()

    @command_dispatcher(commands.ROBOCODE_UPLOAD_TO_NEW_ACTIVITY_INTERNAL)
    def _upload_to_new_activity(
        self, params: UploadNewActivityParamsDict
    ) -> ActionResultDict:
        from robocode_ls_core.progress_report import progress_context

        # When we upload to a new activity, clear the existing cache key.
        self._dir_cache.discard(self.CLOUD_LIST_WORKSPACE_CACHE_KEY)
        with progress_context(
            self._endpoint, "Uploading to new activity package", self._dir_cache
        ):
            directory = params["directory"]
            workspace_id = params["workspaceId"]
            package_name = params["packageName"]
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
        return result.as_dict()
