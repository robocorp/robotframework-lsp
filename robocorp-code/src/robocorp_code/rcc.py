from subprocess import CalledProcessError
import sys
from typing import Optional, List, Any
import weakref

from robocorp_ls_core.basic import implements, as_str
from robocorp_ls_core.constants import NULL
from robocorp_ls_core.protocols import IConfig, IConfigProvider, Sentinel
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_code.protocols import IRcc, IRccWorkspace, IRccRobotMetadata, ActionResult
from pathlib import Path
import os.path
from robocorp_ls_core.protocols import check_implements
from dataclasses import dataclass


log = get_logger(__name__)

RCC_CLOUD_ROBOT_MUTEX_NAME = "rcc_cloud_activity"
RCC_CREDENTIALS_MUTEX_NAME = "rcc_credentials"

ACCOUNT_NAME = "robocorp-code"


def download_rcc(location: str, force: bool = False) -> None:
    """
    Downloads rcc to the given location. Note that we don't overwrite it if it 
    already exists (unless force == True).
    
    :param location:
        The location to store the rcc executable in the filesystem.
    :param force:
        Whether we should overwrite an existing installation.
    """
    from robocorp_ls_core.system_mutex import timed_acquire_mutex

    if not os.path.exists(location) or force:
        with timed_acquire_mutex("robocorp_get_rcc", timeout=120):
            if not os.path.exists(location) or force:
                import platform
                import urllib.request

                machine = platform.machine()
                is_64 = not machine or "64" in machine

                if sys.platform == "win32":
                    if is_64:
                        relative_path = "/windows64/rcc.exe"
                    else:
                        relative_path = "/windows32/rcc.exe"

                elif sys.platform == "darwin":
                    relative_path = "/macos64/rcc"

                else:
                    if is_64:
                        relative_path = "/linux64/rcc"
                    else:
                        relative_path = "/linux32/rcc"

                RCC_VERSION = "v9.16.0"
                prefix = f"https://downloads.robocorp.com/rcc/releases/{RCC_VERSION}"
                url = prefix + relative_path

                log.info(f"Downloading rcc from: {url} to: {location}.")
                response = urllib.request.urlopen(url)

                # Put it all in memory before writing (i.e. just write it if
                # we know we downloaded everything).
                data = response.read()

                try:
                    os.makedirs(os.path.dirname(location))
                except Exception:
                    pass  # Error expected if the parent dir already exists.

                try:
                    with open(location, "wb") as stream:
                        stream.write(data)
                    os.chmod(location, 0x744)
                except Exception:
                    log.exception(
                        "Error writing to: %s.\nParent dir exists: %s",
                        location,
                        os.path.dirname(location),
                    )
                    raise


def get_default_rcc_location() -> str:
    from robocorp_code import get_extension_relative_path

    if sys.platform == "win32":
        location = get_extension_relative_path("bin", "rcc.exe")
    else:
        location = get_extension_relative_path("bin", "rcc")
    return location


class RccRobotMetadata(object):
    def __init__(self, robot_id: str, robot_name: str):
        self._robot_id = robot_id
        self._robot_name = robot_name

    @property
    def robot_id(self) -> str:
        return self._robot_id

    @property
    def robot_name(self) -> str:
        return self._robot_name

    def __typecheckself__(self) -> None:
        _: IRccRobotMetadata = check_implements(self)


class RccWorkspace(object):
    def __init__(self, workspace_id: str, workspace_name: str):
        self._workspace_id = workspace_id
        self._workspace_name = workspace_name

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @property
    def workspace_name(self) -> str:
        return self._workspace_name

    def __typecheckself__(self) -> None:
        _: IRccWorkspace = check_implements(self)


@dataclass
class AccountInfo:
    account: str
    identifier: str
    email: str
    fullname: str


class Rcc(object):
    def __init__(self, config_provider: IConfigProvider) -> None:
        self._config_provider = weakref.ref(config_provider)

        self._last_verified_account_info: Optional[AccountInfo] = None

    @property
    def last_verified_account_info(self) -> Optional[AccountInfo]:
        return self._last_verified_account_info

    def _get_str_optional_setting(self, setting_name) -> Any:
        config_provider = self._config_provider()
        config: Optional[IConfig] = None
        if config_provider is not None:
            config = config_provider.config

        if config:
            return config.get_setting(setting_name, str, None)
        return None

    def _get_robocorp_home(self) -> Optional[str]:
        from robocorp_code.settings import ROBOCORP_HOME

        return self._get_str_optional_setting(ROBOCORP_HOME)

    @property
    def config_location(self) -> Optional[str]:
        """
        @implements(IRcc.config_location)
        """
        # Can be set in tests to provide a different config location.
        from robocorp_code import settings

        return self._get_str_optional_setting(settings.ROBOCORP_RCC_CONFIG_LOCATION)

    @property
    def endpoint(self) -> Optional[str]:
        """
        @implements(IRcc.endpoint)
        """
        # Can be set in tests to provide a different endpoint.
        from robocorp_code import settings

        return self._get_str_optional_setting(settings.ROBOCORP_RCC_ENDPOINT)

    @implements(IRcc.get_rcc_location)
    def get_rcc_location(self) -> str:
        from robocorp_code import settings

        rcc_location = self._get_str_optional_setting(settings.ROBOCORP_RCC_LOCATION)
        if not rcc_location:
            rcc_location = get_default_rcc_location()

        if not os.path.exists(rcc_location):
            download_rcc(rcc_location)
        return rcc_location

    def _run_rcc(
        self,
        args: List[str],
        timeout: float = 30,
        error_msg: str = "",
        mutex_name=None,
        cwd: Optional[str] = None,
        log_errors=True,
        stderr=Sentinel.SENTINEL,
    ) -> ActionResult[str]:
        """
        Returns an ActionResult where the result is the stdout of the executed command.
        
        :param log_errors:
            If false, errors won't be logged (i.e.: should be false when errors
            are expected).
        """
        from robocorp_ls_core.basic import build_subprocess_kwargs
        from subprocess import check_output
        from robocorp_ls_core.subprocess_wrapper import subprocess

        if stderr is Sentinel.SENTINEL:
            stderr = subprocess.PIPE

        rcc_location = self.get_rcc_location()

        env = os.environ.copy()
        env.pop("PYTHONPATH", "")
        env.pop("PYTHONHOME", "")
        env.pop("VIRTUAL_ENV", "")
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        robocorp_home = self._get_robocorp_home()
        if robocorp_home:
            env["ROBOCORP_HOME"] = robocorp_home

        kwargs: dict = build_subprocess_kwargs(cwd, env, stderr=stderr)
        args = [rcc_location] + args + ["--controller", "RobocorpCode"]
        cmdline = " ".join([str(x) for x in args])

        try:
            if mutex_name:
                from robocorp_ls_core.system_mutex import timed_acquire_mutex
            else:
                timed_acquire_mutex = NULL
            with timed_acquire_mutex(mutex_name, timeout=15):
                boutput: bytes = check_output(args, timeout=timeout, **kwargs)

        except CalledProcessError as e:
            stdout = as_str(e.stdout)
            stderr = as_str(e.stderr)
            msg = f"Error running: {cmdline}.\nROBOCORP_HOME: {robocorp_home}\n\nStdout: {stdout}\nStderr: {stderr}"
            if log_errors:
                log.exception(msg)
            if not error_msg:
                return ActionResult(success=False, message=msg)
            else:
                additional_info = [error_msg]
                if stdout or stderr:
                    if stdout and stderr:
                        additional_info.append("\nDetails: ")
                        additional_info.append("\nStdout")
                        additional_info.append(stdout)
                        additional_info.append("\nStderr")
                        additional_info.append(stderr)

                    elif stdout:
                        additional_info.append("\nDetails: ")
                        additional_info.append(stdout)

                    elif stderr:
                        additional_info.append("\nDetails: ")
                        additional_info.append(stderr)

                return ActionResult(success=False, message="".join(additional_info))

        except Exception:
            msg = f"Error running: {args}"
            log.exception(msg)
            return ActionResult(success=False, message=msg)

        output = boutput.decode("utf-8", "replace")

        log.debug("Output from: %s:\n%s", cmdline, output)
        return ActionResult(success=True, message=None, result=output)

    _TEMPLATES = {
        "standard": "Standard - Robot Framework Robot.",
        "python": "Python - Python Robot.",
        "extended": "Extended - Robot Framework Robot with additional scaffolding.",
    }

    @implements(IRcc.get_template_names)
    def get_template_names(self) -> ActionResult[List[str]]:
        result = self._run_rcc("robot initialize -l".split())
        if not result.success:
            return ActionResult(success=False, message=result.message)

        output = result.result
        if output is None:
            return ActionResult(success=False, message="Output not available")
        templates = set()
        for line in output.splitlines():
            if line.startswith("- "):
                template_name = line[2:].strip()
                templates.add(template_name)

        ret: List[str] = []
        for key, description in self._TEMPLATES.items():
            if key in templates:
                ret.append(description)

        return ActionResult(success=True, message=None, result=ret)

    def _add_config_to_args(self, args: List[str]) -> List[str]:
        config_location = self.config_location
        if config_location:
            args.append("--config")
            args.append(config_location)
        return args

    def _add_account_to_args(self, args: List[str]) -> Optional[ActionResult]:
        """
        Adds the account to the args.
        
        Returns an error ActionResult if unable to get a valid account.
        """
        account_info = self._last_verified_account_info
        if account_info is None:
            account_info = self.get_valid_account_info()
            if account_info is None:
                return ActionResult(False, "Unable to get valid account for action.")

        args.append("--account")
        args.append(account_info.account)
        return None

    @implements(IRcc.create_robot)
    def create_robot(self, template: str, directory: str) -> ActionResult:
        if template not in self._TEMPLATES:
            # Check if we can translate from the description
            for key, description in self._TEMPLATES.items():
                if description == template:
                    template = key
                    break

        args = ["robot", "initialize", "-t", template, "-d", directory]
        args = self._add_config_to_args(args)
        return self._run_rcc(args, error_msg="Error creating robot.")

    @implements(IRcc.add_credentials)
    def add_credentials(self, credential: str) -> ActionResult:
        self._last_verified_account_info = None
        args = ["config", "credentials"]
        endpoint = self.endpoint
        if endpoint:
            args.append("--endpoint")
            args.append(endpoint)

        args = self._add_config_to_args(args)
        args.append("--account")
        args.append(ACCOUNT_NAME)

        args.append(credential)

        return self._run_rcc(args, mutex_name=RCC_CREDENTIALS_MUTEX_NAME)

    @implements(IRcc.remove_current_credentials)
    def remove_current_credentials(self) -> ActionResult:
        self._last_verified_account_info = None
        args = ["config", "credentials"]
        args.append("--account")
        args.append(ACCOUNT_NAME)
        args.append("--delete")
        args = self._add_config_to_args(args)
        return self._run_rcc(args, mutex_name=RCC_CREDENTIALS_MUTEX_NAME)

    @implements(IRcc.credentials_valid)
    def credentials_valid(self) -> bool:
        account = self.get_valid_account_info()
        return account is not None

    def get_valid_account_info(self) -> Optional[AccountInfo]:
        import json

        self._last_verified_account_info = None
        args = [
            "config",
            "credentials",
            "-j",
            "--verified",
            # Note: it doesn't really filter in this case, so, filter it
            # manually afterwards.
            # "--account",
            # ACCOUNT_NAME,
        ]
        endpoint = self.endpoint
        if endpoint:
            args.append("--endpoint")
            args.append(endpoint)

        args = self._add_config_to_args(args)

        result = self._run_rcc(args, mutex_name=RCC_CREDENTIALS_MUTEX_NAME)
        if not result.success:
            msg = f"Error checking credentials: {result.message}"
            log.critical(msg)
            return None

        output = result.result
        if not output:
            msg = f"Error. Expected to get info on credentials (found no output)."
            log.critical(msg)
            return None

        try:
            credentials = json.loads(output)
            credentials = [
                credential
                for credential in credentials
                if credential.get("account", "").lower() == ACCOUNT_NAME
            ]

            for credential in credentials:
                timestamp = credential.get("verified")
                if timestamp and int(timestamp):

                    details = credential.get("details", {})
                    if not isinstance(details, dict):
                        email = "<Email:Unknown>"
                        fullname = "<Name: Unknown>"
                    else:
                        email = str(details.get("email", "<Email: Unknown>"))
                        fullname = (
                            f'{details.get("first_name")} {details.get("last_name")}'
                        )

                    account = self._last_verified_account_info = AccountInfo(
                        credential["account"], credential["identifier"], email, fullname
                    )

                    return account
        except:
            log.exception("Error loading credentials from: %s", output)

        # Found no valid credential
        return None

    @implements(IRcc.cloud_list_workspaces)
    def cloud_list_workspaces(self) -> ActionResult[List[IRccWorkspace]]:
        import json

        ret: List[IRccWorkspace] = []
        args = ["cloud", "workspace"]
        args = self._add_config_to_args(args)
        error_action_result = self._add_account_to_args(args)
        if error_action_result is not None:
            return error_action_result

        result = self._run_rcc(args, mutex_name=RCC_CLOUD_ROBOT_MUTEX_NAME)

        if not result.success:
            return ActionResult(False, result.message)

        output = result.result
        if not output:
            return ActionResult(
                False, "Error listing cloud workspaces (output not available)."
            )

        try:
            lst = json.loads(output)
        except Exception as e:
            log.exception(f"Error parsing json: {output}")
            return ActionResult(
                False,
                f"Error loading json obtained while listing cloud workspaces.\n{e}",
            )
        for workspace_info in lst:
            ret.append(
                RccWorkspace(
                    workspace_id=workspace_info["id"],
                    workspace_name=workspace_info["name"],
                )
            )
        return ActionResult(True, None, ret)

    @implements(IRcc.cloud_list_workspace_robots)
    def cloud_list_workspace_robots(
        self, workspace_id: str
    ) -> ActionResult[List[IRccRobotMetadata]]:
        import json

        ret: List[IRccRobotMetadata] = []
        args = ["cloud", "workspace"]
        args.extend(("--workspace", workspace_id))

        args = self._add_config_to_args(args)
        error_action_result = self._add_account_to_args(args)
        if error_action_result is not None:
            return error_action_result

        result = self._run_rcc(args, mutex_name=RCC_CLOUD_ROBOT_MUTEX_NAME)
        if not result.success:
            return ActionResult(False, result.message)

        output = result.result
        if not output:
            return ActionResult(
                False, "Error listing cloud workspace robots (output not available)."
            )

        try:
            workspace_info = json.loads(output)
        except Exception as e:
            log.exception(f"Error parsing json: {output}")
            return ActionResult(
                False,
                f"Error loading json obtained while listing cloud workspaces activities.\n{e}",
            )

        if not isinstance(workspace_info, dict):
            log.critical(f"Expected dict as top-level from json: {output}")
            msg = f"Unexpected type of cloud workspace activity json (expected dict, found: {type(workspace_info)}"
            return ActionResult(False, msg)

        for activity_info in workspace_info.get("activities", []):
            ret.append(
                RccRobotMetadata(
                    robot_id=activity_info["id"], robot_name=activity_info["name"]
                )
            )
        return ActionResult(True, None, ret)

    @implements(IRcc.cloud_set_robot_contents)
    def cloud_set_robot_contents(
        self, directory: str, workspace_id: str, robot_id: str
    ) -> ActionResult:

        if not os.path.exists(directory):
            return ActionResult(
                False, f"Expected: {directory} to exist to upload to the cloud."
            )
        if not os.path.isdir(directory):
            return ActionResult(
                False,
                f"Expected: {directory} to be a directory to upload to the cloud.",
            )

        args = ["cloud", "push"]
        args.extend(["--directory", directory])
        args.extend(["--workspace", workspace_id])
        args.extend(["--robot", robot_id])

        args = self._add_config_to_args(args)
        error_action_result = self._add_account_to_args(args)
        if error_action_result is not None:
            return error_action_result

        ret = self._run_rcc(args, mutex_name=RCC_CLOUD_ROBOT_MUTEX_NAME)
        return ret

    @implements(IRcc.cloud_create_robot)
    def cloud_create_robot(
        self, workspace_id: str, robot_name: str
    ) -> ActionResult[str]:
        from robocorp_ls_core.subprocess_wrapper import subprocess

        args = ["cloud", "new"]
        args.extend(["--workspace", workspace_id])
        args.extend(["--robot", robot_name])

        args = self._add_config_to_args(args)
        error_action_result = self._add_account_to_args(args)
        if error_action_result is not None:
            return error_action_result

        ret = self._run_rcc(
            args, mutex_name=RCC_CLOUD_ROBOT_MUTEX_NAME, stderr=subprocess.STDOUT
        )
        if not ret.success:
            return ret

        try:
            # Note: result is the package id.
            stdout = ret.result
            if not stdout:
                return ActionResult(
                    False, f"No process stdout when creating new cloud package."
                )
            stdout = stdout.strip()

            # stdout is something as:
            # Created new robot named 'New package' with identity 1414.
            if not stdout.lower().startswith("created new"):
                return ActionResult(
                    False,
                    f'Expected output to start with "Created new". Found: {stdout}',
                )

            if stdout.endswith("."):
                stdout = stdout[:-1]

            package_id = stdout.split(" ")[-1]
            if not package_id:
                return ActionResult(
                    False, f"Unable to extract package id from: {stdout}"
                )
        except Exception as e:
            log.exception("Error creating new robot.")
            return ActionResult(
                False, f"Unable to extract robot id from: {stdout}. Error: {e}"
            )

        return ActionResult(ret.success, None, package_id)

    @implements(IRcc.get_robot_yaml_environ)
    def get_robot_yaml_environ(
        self, robot_yaml_path: Path, env_json_path: Optional[Path], timeout=None
    ) -> ActionResult[str]:
        args = ["env", "variables", "-r", str(robot_yaml_path)]
        if env_json_path:
            args.append("-e")
            args.append(str(env_json_path))
        args.append("-j")
        ret = self._run_rcc(
            args,
            mutex_name=RCC_CLOUD_ROBOT_MUTEX_NAME,
            cwd=str(robot_yaml_path.parent),
            timeout=timeout,  # Creating the env may be really slow!
        )
        return ret

    @implements(IRcc.run_python_code_robot_yaml)
    def run_python_code_robot_yaml(
        self,
        python_code: str,
        conda_yaml_str_contents: Optional[str],
        silent: bool = True,
        timeout=None,
    ) -> ActionResult[str]:
        from robocorp_ls_core import yaml_wrapper

        # The idea is obtaining a temporary directory, creating the needed
        # python file, robot.yaml and conda file and then executing an activity
        # that'll execute the python file.
        directory = make_numbered_in_temp(lock_timeout=60 * 60)

        python_file: Path = directory / "code_to_exec.py"
        python_file.write_text(python_code, encoding="utf-8")

        # Note that the environ is not set (because the activityRoot cannot be
        # set to a non-relative directory copying the existing environ leads to
        # wrong results).
        robot_yaml: Path = directory / "robot.yaml"
        p: dict = {
            "tasks": {"Run Python Command": {"command": ["python", str(python_file)]}},
            "artifactsDir": "output",
        }
        if conda_yaml_str_contents:
            p["condaConfigFile"] = "conda.yaml"
            conda_file: Path = directory / "conda.yaml"
            conda_file.write_text(conda_yaml_str_contents, encoding="utf-8")

        robot_yaml.write_text(yaml_wrapper.dumps(p), encoding="utf-8")

        args = ["task", "run", "-r", str(robot_yaml)]
        if silent:
            args.append("--silent")
        ret = self._run_rcc(
            args,
            mutex_name=RCC_CLOUD_ROBOT_MUTEX_NAME,
            cwd=str(directory),
            timeout=timeout,  # Creating the env may be really slow!
        )
        return ret

    @implements(IRcc.check_conda_installed)
    def check_conda_installed(self, timeout=None) -> ActionResult[str]:
        # With mamba this is not needed anymore.
        # Note: api kept just for backward compatibility.
        return ActionResult(success=True, message=None, result="OK.")

    @implements(IRcc.feedack_metric)
    def feedack_metric(self, name, value="+1") -> ActionResult[str]:
        return self._run_rcc(
            ["feedback", "metric", "-t", "vscode", "-n", name, "-v", value],
            mutex_name=None,
            log_errors=False,
        )

    def __typecheckself__(self) -> None:
        _: IRcc = check_implements(self)

    def configuration_diagnostics(self, robot_yaml, json=True) -> ActionResult[str]:
        return self._run_rcc(
            ["configuration", "diagnostics"]
            + (["--json"] if json else [])
            + ["-r", robot_yaml],
            mutex_name=None,
        )


def make_numbered_in_temp(
    keep: int = 10,
    lock_timeout: float = -1,
    tmpdir: Optional[Path] = None,
    register=None,
) -> Path:
    """
    Helper to create a numbered directory in the temp dir with automatic disposal
    of old contents.
    """
    import tempfile
    from robocorp_code.path_operations import get_user
    from robocorp_code.path_operations import make_numbered_dir_with_cleanup
    from robocorp_code.path_operations import LOCK_TIMEOUT

    user = get_user() or "unknown"
    temproot = tmpdir if tmpdir else Path(tempfile.gettempdir())
    rootdir = temproot / f"robocorp-code-{user}"
    rootdir.mkdir(exist_ok=True)
    return make_numbered_dir_with_cleanup(
        prefix="rcc-",
        root=rootdir,
        keep=keep,
        lock_timeout=lock_timeout if lock_timeout > 0 else LOCK_TIMEOUT,
        register=register,
    )
