import sys
from typing import Optional, List, Any, Generic, TypeVar, Dict
from pathlib import Path


# Hack so that we don't break the runtime on versions prior to Python 3.8.
if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass

    class TypedDict(object):
        pass


else:
    from typing import Protocol
    from typing import TypedDict


class LocalRobotMetadataInfoDict(TypedDict):
    directory: str  # The directory that contains the robot.yaml
    filePath: str  # The path to the robot.yaml
    name: str  # The name of the robot
    yamlContents: dict  # The contents of the robot.yaml


class PackageInfoDict(TypedDict):
    name: str
    id: str
    sortKey: str
    workspaceId: str
    workspaceName: str


class PackageInfoInLRUDict(TypedDict):
    workspace_id: str
    package_id: str
    directory: str
    time: float


class WorkspaceInfoDict(TypedDict):
    workspaceName: str
    workspaceId: str
    packages: List[PackageInfoDict]


T = TypeVar("T")


class ActionResult(Generic[T]):

    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[T]

    def __init__(
        self, success: bool, message: Optional[str] = None, result: Optional[T] = None
    ):
        self.success = success
        self.message = message
        self.result = result

    def as_dict(self):
        return {"success": self.success, "message": self.message, "result": self.result}

    def __str__(self):
        return f"ActionResult(success={self.success!r}, message={self.message!r}, result={self.result!r})"

    __repr__ = __str__


class ActionResultDict(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Any


class ActionResultDictRobotLaunch(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[dict]


class ActionResultDictLocalRobotMetadata(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[List[LocalRobotMetadataInfoDict]]


class ListWorkspacesActionResultDict(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[List[WorkspaceInfoDict]]


class CloudLoginParamsDict(TypedDict):
    credentials: str


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


class IRccWorkspace(Protocol):
    @property
    def workspace_id(self) -> str:
        pass

    @property
    def workspace_name(self) -> str:
        pass


class IRccRobotMetadata(Protocol):
    @property
    def robot_id(self) -> str:
        pass

    @property
    def robot_name(self) -> str:
        pass


class IRcc(Protocol):
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

    def get_template_names(self) -> ActionResult[List[str]]:
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

    def get_robot_yaml_environ(
        self, robot_yaml_path: Path, env_json_path: Optional[Path], timeout=None
    ) -> ActionResult[str]:
        """
        """

    def run_python_code_robot_yaml(
        self,
        python_code: str,
        conda_yaml_str_contents: Optional[str],
        silent: bool = True,
        timeout=None,
    ) -> ActionResult[str]:
        """
        Runs the given code based on an existing robot yaml.
        
        IMPORTANT: this can be a really slow operation on the first activation to 
        create the env.
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
