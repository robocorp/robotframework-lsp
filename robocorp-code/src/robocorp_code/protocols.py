import sys
from pathlib import Path
from typing import Any, ContextManager, Dict, List, Optional, Tuple, TypeVar

# Backward-compatibility imports:
from robocorp_ls_core.protocols import ActionResult, ActionResultDict  # noqa

# Hack so that we don't break the runtime on versions prior to Python 3.8.
if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass

    class TypedDict(object):
        pass

else:
    from typing import Protocol, TypedDict


class LocalRobotMetadataInfoDict(TypedDict):
    directory: str  # The directory that contains the robot.yaml
    filePath: str  # The path to the robot.yaml
    name: str  # The name of the robot
    yamlContents: dict  # The contents of the robot.yaml


class LocatorEntryInfoDict(TypedDict):
    name: str
    line: int
    column: int
    type: str  # "browser" or "image"
    filePath: str


class PackageInfoDict(TypedDict):
    name: str
    id: str
    sortKey: str
    workspaceId: str
    workspaceName: str
    organizationName: str


class PackageInfoInLRUDict(TypedDict):
    workspace_id: str
    package_id: str
    directory: str
    time: float


class WorkspaceInfoDict(TypedDict):
    organizationName: str
    workspaceName: str
    workspaceId: str
    packages: List[PackageInfoDict]


T = TypeVar("T")


class ActionResultDictRobotLaunch(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[Dict[str, Any]]


class ActionResultDictLocatorsJson(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[Tuple[Any, Path]]


class ActionResultDictLocatorsJsonInfo(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[List[LocatorEntryInfoDict]]


class ActionResultDictLocalRobotMetadata(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[List[LocalRobotMetadataInfoDict]]


class WorkItem(TypedDict):
    name: str
    json_path: str  # Full path to the json represented by this work item


class WorkItemsInfo(TypedDict):
    robot_yaml: str  # Full path to the robot which has these work item info

    # Full path to the place where input work items are located
    input_folder_path: str

    # Full path to the place where output work items are located
    output_folder_path: str

    input_work_items: List[WorkItem]
    output_work_items: List[WorkItem]

    new_output_workitem_path: str


class ActionResultDictWorkItems(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[WorkItemsInfo]


class ListWorkItemsParams(TypedDict):
    robot: str  # Path to the robot for which we want the work items (may be just the folder or the yaml).
    output_prefix: str  # Prefix for output folder (such as 'run-' or 'interactive-').
    increment_output: bool  # Whether a new output folder should be generated (and older ones should be collected).


class ListActionsParams(TypedDict):
    action_package: str  # Path to the action package for which we want the actions (may be just the folder or the package.yaml).


class ListWorkspacesActionResultDict(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[List[WorkspaceInfoDict]]


class RobotTemplate(TypedDict):
    name: str
    description: str


class CloudLoginParamsDict(TypedDict):
    credentials: str


class AuthorizeTokenDict(TypedDict):
    token: str
    endpoint: str


class ConfigurationDiagnosticsDict(TypedDict):
    robotYaml: str


class CloudListWorkspaceDict(TypedDict):
    refresh: bool  # False means we can use the last cached results and True means it should be updated.


class CreateRobotParamsDict(TypedDict):
    directory: str
    template: str
    name: str


class RunInRccParamsDict(TypedDict):
    args: List[str]


class UploadRobotParamsDict(TypedDict):
    workspaceId: str
    robotId: str
    directory: str


class UploadNewRobotParamsDict(TypedDict):
    workspaceId: str
    robotName: str
    directory: str


class ProfileImportParamsDict(TypedDict):
    profileUri: str


class ProfileSwitchParamsDict(TypedDict):
    profileName: str


class ProfileListResultTypedDict(TypedDict):
    current: str
    profiles: dict  # name to description


class IRccWorkspace(Protocol):
    @property
    def workspace_id(self) -> str:
        pass

    @property
    def workspace_name(self) -> str:
        pass

    @property
    def organization_name(self) -> str:
        pass


class IRccRobotMetadata(Protocol):
    @property
    def robot_id(self) -> str:
        pass

    @property
    def robot_name(self) -> str:
        pass


class IRCCSpaceInfo(Protocol):
    space_name: str

    def load_last_usage(self, none_if_not_found: bool = False) -> Optional[float]:
        pass

    def update_last_usage(self) -> float:
        pass

    def load_requested_pid(self) -> str:
        pass

    def has_timeout_elapsed(self, timeout_to_reuse_space: float) -> bool:
        pass

    def acquire_lock(self) -> ContextManager:
        pass

    def conda_contents_match(self, conda_yaml_contents: str) -> bool:
        pass

    def matches_conda_identity_yaml(self, conda_id: Path) -> bool:
        pass


class IRobotYamlEnvInfo(Protocol):
    @property
    def env(self) -> Dict[str, str]:
        pass

    @property
    def space_info(self) -> IRCCSpaceInfo:
        pass


class IRccListener(Protocol):
    def before_command(self, args: List[str]):
        pass


class IRcc(Protocol):
    rcc_listeners: List[IRccListener]

    @property
    def endpoint(self) -> Optional[str]:
        """
        Read-only property specifying the endopoint to be used (gotten from settings).
        """

    @property
    def config_location(self) -> Optional[str]:
        """
        Read-only property specifying the config location to be used (gotten from settings).
        """

    def get_rcc_location(self) -> str:
        pass

    def get_robocorp_home_from_settings(self) -> Optional[str]:
        """
        If ROBOCORP_HOME is defined from the settings, its location is returned,
        otherwise it returns None.
        """

    def get_robocorp_code_datadir(self) -> Path:
        """
        Provides the directory to store info for robocorp code.

        Usually ROBOCORP_HOME/.robocorp_code
        """

    def get_template_names(self) -> ActionResult[List[RobotTemplate]]:
        pass

    def create_robot(self, template: str, directory: str) -> ActionResult:
        """
        :param template:
            The template to create.
        :param directory:
            The directory where the robot should be created.
        """

    def cloud_set_robot_contents(
        self, directory: str, workspace_id: str, robot_id: str
    ) -> ActionResult:
        """
        Note: needs connection to the cloud.
        """

    def add_credentials(self, credential: str) -> ActionResult:
        pass

    def remove_current_credentials(self) -> ActionResult:
        pass

    def credentials_valid(self) -> bool:
        """
        Note: needs connection to the cloud.
        """

    def cloud_authorize_token(
        self, workspace_id: str
    ) -> ActionResult[AuthorizeTokenDict]:
        pass

    def cloud_list_workspaces(self) -> ActionResult[List[IRccWorkspace]]:
        """
        Note: needs connection to the cloud.
        """

    def cloud_list_workspace_robots(
        self, workspace_id: str
    ) -> ActionResult[List[IRccRobotMetadata]]:
        """
        Note: needs connection to the cloud.
        """

    def cloud_create_robot(
        self, workspace_id: str, robot_name: str
    ) -> ActionResult[str]:
        """
        Note: needs connection to the cloud.

        :returns an action result with the robot id created.
        """

    def get_robot_yaml_env_info(
        self,
        robot_yaml_path: Path,
        conda_yaml_path: Path,
        conda_yaml_contents: str,
        env_json_path: Optional[Path],
        timeout=None,
        holotree_manager=None,
        on_env_creation_error=None,
    ) -> ActionResult[IRobotYamlEnvInfo]:
        """
        :returns: the result of getting the robot environment. It's expected that
                  the dict contains a 'PYTHON_EXE' with the python executable
                  to be used.
        """

    def check_conda_installed(self, timeout=None) -> ActionResult[str]:
        """
        Makes sure that conda is installed (i.e.: rcc conda check -i).

        Note: this can be a really slow operation on the first activation to
        download conda.
        """

    def feedack_metric(self, name, value="+1"):
        """
        i.e.: Something as:
        rcc feedback metric -t vscode -n vscode.cloud.upload.existing -v +1
        """

    def profile_import(self, profile_path: str) -> ActionResult:
        pass

    def profile_switch(self, profile_name: str) -> ActionResult:
        pass

    def profile_list(self) -> ActionResult[ProfileListResultTypedDict]:
        pass

    def configuration_diagnostics(self, robot_yaml, json=True) -> ActionResult[str]:
        pass

    def configuration_settings(self) -> ActionResult[str]:
        pass

    def holotree_import(self, zip_file: Path, enable_shared: bool) -> ActionResult[str]:
        pass

    def holotree_variables(
        self, robot_yaml: Path, space_name: str, no_build: bool
    ) -> ActionResult[str]:
        pass
