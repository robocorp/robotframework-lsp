import json
import os.path
import sys
import time
import weakref
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired, list2cmdline
from typing import Any, Dict, List, Optional, Set

from robocorp_ls_core.basic import as_str, implements, is_process_alive
from robocorp_ls_core.constants import NULL
from robocorp_ls_core.protocols import (
    IConfig,
    IConfigProvider,
    RCCActionResult,
    Sentinel,
    check_implements,
)
from robocorp_ls_core.robotframework_log import get_log_level, get_logger

from robocorp_code.protocols import (
    ActionResult,
    AuthorizeTokenDict,
    IRcc,
    IRccListener,
    IRccRobotMetadata,
    IRccWorkspace,
    IRobotYamlEnvInfo,
    ProfileListResultTypedDict,
    RobotTemplate,
)
from robocorp_code.rcc_space_info import RCCSpaceInfo, SpaceState

log = get_logger(__name__)

RCC_CLOUD_ROBOT_MUTEX_NAME = "rcc_cloud_activity"
RCC_CREDENTIALS_MUTEX_NAME = "rcc_credentials"

ACCOUNT_NAME = "robocorp-code"


def download_rcc(
    location: str, force: bool = False, sys_platform: Optional[str] = None
) -> None:
    """
    Downloads rcc to the given location. Note that we don't overwrite it if it
    already exists (unless force == True).

    :param location:
        The location to store the rcc executable in the filesystem.
    :param force:
        Whether we should overwrite an existing installation.
    """
    from robocorp_ls_core.system_mutex import timed_acquire_mutex

    if sys_platform is None:
        sys_platform = sys.platform

    if not os.path.exists(location) or force:
        with timed_acquire_mutex("robocorp_get_rcc", timeout=120):
            if not os.path.exists(location) or force:
                import platform
                import urllib.request

                machine = platform.machine()
                is_64 = not machine or "64" in machine

                if sys_platform == "win32":
                    if is_64:
                        relative_path = "/windows64/rcc.exe"
                    else:
                        relative_path = "/windows32/rcc.exe"

                elif sys_platform == "darwin":
                    relative_path = "/macos64/rcc"

                else:
                    if is_64:
                        relative_path = "/linux64/rcc"
                    else:
                        relative_path = "/linux32/rcc"

                RCC_VERSION = "v17.28.4"
                prefix = f"https://downloads.robocorp.com/rcc/releases/{RCC_VERSION}"
                url = prefix + relative_path

                log.info(f"Downloading rcc from: {url} to: {location}.")

                # Cloudflare seems to be blocking "User-Agent: Python-urllib/3.9".
                # Use a different one as that must be sorted out.
                response = urllib.request.urlopen(
                    urllib.request.Request(url, headers={"User-Agent": "Mozilla"})
                )

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


def get_default_robocorp_home_location() -> Path:
    if sys.platform == "win32":
        path = r"$LOCALAPPDATA\robocorp"
    else:
        path = r"$HOME/.robocorp"
    robocorp_home_str = os.path.expandvars(path)
    return Path(robocorp_home_str)


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
    def __init__(self, workspace_id: str, workspace_name: str, organization_name: str):
        self._workspace_id = workspace_id
        self._workspace_name = workspace_name
        self._organization_name = organization_name

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @property
    def workspace_name(self) -> str:
        return self._workspace_name

    @property
    def organization_name(self) -> str:
        return self._organization_name

    def __typecheckself__(self) -> None:
        _: IRccWorkspace = check_implements(self)


@dataclass
class AccountInfo:
    account: str
    identifier: str
    email: str
    fullname: str


class RobotInfoEnv(object):
    def __init__(self, env: Dict[str, str], space_info: RCCSpaceInfo):
        self.env = env
        self.space_info = space_info

    def __typecheckself__(self) -> None:
        _: IRobotYamlEnvInfo = check_implements(self)


class Rcc(object):
    # Note that this is stored in the class, not in the instance.
    # It should store the contents of conda which couldn't be resolved.
    # After being stored once here, it'll only be tried again when
    # the user restarts the language server (or changes the conda config).
    broken_conda_configs: Dict[str, ActionResult] = {}

    def __init__(self, config_provider: IConfigProvider) -> None:
        self._config_provider = weakref.ref(config_provider)

        self._last_verified_account_info: Optional[AccountInfo] = None
        self.rcc_listeners: List[IRccListener] = []
        self._feedback_metrics_reported: Set[str] = set()

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

    def get_robocorp_home_from_settings(self) -> Optional[str]:
        from robocorp_code.settings import ROBOCORP_HOME

        return self._get_str_optional_setting(ROBOCORP_HOME)

    def get_robocorp_code_datadir(self) -> Path:
        robocorp_home_str = self.get_robocorp_home_from_settings()
        if not robocorp_home_str:
            robocorp_home = get_default_robocorp_home_location()
        else:
            robocorp_home = Path(robocorp_home_str)

        directory = robocorp_home / ".robocorp_code"
        return directory

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
        timeout: float = 35,
        error_msg: str = "",
        mutex_name=None,
        cwd: Optional[str] = None,
        log_errors=True,
        stderr=Sentinel.SENTINEL,
        show_interactive_output: bool = False,
        hide_in_log: Optional[str] = None,
    ) -> RCCActionResult:
        """
        Returns an ActionResult where the result is the stdout of the executed command.

        :param log_errors:
            If false, errors won't be logged (i.e.: should be false when errors
            are expected).

        :param stderr:
            If given sets the stderr redirection (by default it's subprocess.PIPE,
            but users could change it to something as subprocess.STDOUT).
        """
        from subprocess import check_output

        from robocorp_ls_core.basic import build_subprocess_kwargs
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

        robocorp_home = self.get_robocorp_home_from_settings()
        if robocorp_home:
            env["ROBOCORP_HOME"] = robocorp_home

        kwargs: dict = build_subprocess_kwargs(cwd, env, stderr=stderr)
        args = [rcc_location] + args + ["--controller", "RobocorpCode"]
        cmdline = list2cmdline([str(x) for x in args])

        try:
            if mutex_name:
                from robocorp_ls_core.system_mutex import timed_acquire_mutex
            else:
                timed_acquire_mutex = NULL
            with timed_acquire_mutex(mutex_name, timeout=15):
                if get_log_level() >= 2:
                    msg = f"Running: {cmdline}"
                    if hide_in_log:
                        msg = msg.replace(hide_in_log, "<HIDDEN_IN_LOG>")

                    log.debug(msg)

                curtime = time.time()
                for listener in self.rcc_listeners:
                    listener.before_command(args)

                boutput: bytes
                # We have 2 main modes here: one in which we can print the output
                # interactively while the command is running and another where
                # we only print if some error happened.
                if not show_interactive_output:
                    boutput = check_output(args, timeout=timeout, **kwargs)
                else:
                    from robocorp_ls_core.progress_report import (
                        get_current_progress_reporter,
                    )

                    from robocorp_code.subprocess_check_output_interactive import (
                        check_output_interactive,
                    )

                    progress_reporter = get_current_progress_reporter()

                    def on_output(content):
                        try:
                            sys.stderr.buffer.write(content)

                            # Besides writing it to stderr, let's also add more
                            # info to our current progress (if any).
                            if progress_reporter is not None:
                                progress_reporter.set_additional_info(
                                    content.decode("utf-8", "replace")
                                )
                        except:
                            log.exception("Error reporting interactive output.")

                    boutput = check_output_interactive(
                        args,
                        timeout=timeout,
                        on_stderr=on_output,
                        on_stdout=on_output,
                        progress_reporter=progress_reporter,
                        **kwargs,
                    )

        except CalledProcessError as e:
            stdout = as_str(e.stdout)
            stderr = as_str(e.stderr)
            msg = f"Error running: {cmdline}.\nROBOCORP_HOME: {robocorp_home}\n\nStdout: {stdout}\nStderr: {stderr}"
            if hide_in_log:
                msg = msg.replace(hide_in_log, "<HIDDEN_IN_LOG>")

            if log_errors:
                log.exception(msg)
            if not error_msg:
                return RCCActionResult(cmdline, success=False, message=msg)
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

                return RCCActionResult(
                    cmdline, success=False, message="".join(additional_info)
                )

        except TimeoutExpired:
            msg = f"Timed out ({timeout}s elapsed) when running: {cmdline}"
            log.exception(msg)
            return RCCActionResult(cmdline, success=False, message=msg)

        except Exception:
            msg = f"Error running: {cmdline}"
            log.exception(msg)
            return RCCActionResult(cmdline, success=False, message=msg)

        output = boutput.decode("utf-8", "replace")

        do_log_as_info = (log_errors and get_log_level() >= 1) or get_log_level() >= 2
        if do_log_as_info:
            elapsed = time.time() - curtime
            msg = f"Output from: {cmdline} (took: {elapsed:.2f}s): {output}"
            if hide_in_log:
                msg = msg.replace(hide_in_log, "<HIDDEN_IN_LOG>")
            log.info(msg)

        return RCCActionResult(cmdline, success=True, message=None, result=output)

    @implements(IRcc.get_template_names)
    def get_template_names(self) -> ActionResult[List[RobotTemplate]]:
        result = self._run_rcc("robot initialize -l --json".split())
        if not result.success:
            return ActionResult(success=False, message=result.message)

        if result.result is None:
            return ActionResult(success=False, message="Output not available")

        output: Dict[str, str] = {}
        try:
            output = json.loads(result.result)
        except json.decoder.JSONDecodeError as e:
            return ActionResult(success=False, message=f"Invalid output format: {e}")
        templates: List[RobotTemplate] = []
        for name, description in output.items():
            template: RobotTemplate = {"name": name, "description": description}
            templates.append(template)

        return ActionResult(success=True, message=None, result=templates)

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

    @implements(IRcc.profile_import)
    def profile_import(self, profile_path: str) -> ActionResult:
        args = ["config", "import", "-f", profile_path]
        args = self._add_config_to_args(args)
        return self._run_rcc(args, error_msg="Error importing profile.")

    @implements(IRcc.profile_switch)
    def profile_switch(self, profile_name: str) -> ActionResult:
        if profile_name == "<remove-current-back-to-defaults>":
            args = ["config", "switch", "-n"]
        else:
            args = ["config", "switch", "-p", profile_name]
        args = self._add_config_to_args(args)
        return self._run_rcc(args, error_msg="Error switching profile.")

    @implements(IRcc.profile_list)
    def profile_list(self) -> ActionResult[ProfileListResultTypedDict]:
        """
        Result is something as:

        {
          "current": "default",
          "profiles": {
            "beta": "<description>"
            "charlie": "<description>"
          }
        }
        """
        args = ["config", "switch", "-j"]
        args = self._add_config_to_args(args)
        ret = self._run_rcc(args, error_msg="Error listing profiles.")
        if not ret.success:
            return ActionResult(False, ret.message, None)
        try:
            assert ret.result
            return ActionResult(True, None, json.loads(ret.result))
        except Exception as e:
            message = f"Error loading result as json. {e}"
            log.exception(message)
            return ActionResult(False, message, None)

    @implements(IRcc.create_robot)
    def create_robot(
        self, template: str, directory: str, force: bool = False
    ) -> ActionResult:
        args = ["robot", "initialize", "-t", template, "-d", directory]
        if force:
            args.append("-f")
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

        return self._run_rcc(
            args, mutex_name=RCC_CREDENTIALS_MUTEX_NAME, hide_in_log=credential
        )

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

    @implements(IRcc.cloud_authorize_token)
    def cloud_authorize_token(self, workspace_id) -> ActionResult[AuthorizeTokenDict]:
        args = ["cloud", "authorize"]

        args = self._add_config_to_args(args)

        args.append("--workspace")
        args.append(workspace_id)

        args.append("--minutes")

        config_provider = self._config_provider()
        config: Optional[IConfig] = None
        timeout = 30
        if config_provider is not None:
            config = config_provider.config
            if config:
                from robocorp_code.settings import (
                    ROBOCORP_VAULT_TOKEN_TIMEOUT_IN_MINUTES,
                )

                timeout = config.get_setting(
                    ROBOCORP_VAULT_TOKEN_TIMEOUT_IN_MINUTES, int, 30
                )

        if timeout >= 60:
            log.info(
                "Timeout changed from %s to %s (in minutes). Please use Robocorp Control Room or Robocorp Assistant for longer runs.",
                timeout,
                60,
            )
            timeout = 60
        elif timeout < 5:
            log.info("Timeout changed from %s to %s (in minutes).", timeout, 5)
            timeout = 5

        args.append(f"{round(timeout)}")

        # Always reuse it for 1:30 right now.
        args.append("--graceperiod")
        args.append("90")

        error_action_result = self._add_account_to_args(args)
        if error_action_result is not None:
            return error_action_result

        result = self._run_rcc(args, log_errors=False)

        if not result.success:
            return ActionResult(False, result.message)

        output = result.result
        if not output:
            return ActionResult(
                False, "Error in cloud authorize (output not available)."
            )

        try:
            as_dict = json.loads(output)
        except Exception:
            msg = "Unable to load json from cloud authorize."
            log.exception(msg)
            return ActionResult(False, msg)
        else:
            return ActionResult(
                True, None, {"token": as_dict["token"], "endpoint": as_dict["endpoint"]}
            )

    @implements(IRcc.cloud_list_workspaces)
    def cloud_list_workspaces(self) -> ActionResult[List[IRccWorkspace]]:
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
                False, "Error listing Control Room workspaces (output not available)."
            )

        try:
            lst = json.loads(output)
        except Exception as e:
            log.exception(f"Error parsing json: {output}")
            return ActionResult(
                False,
                f"Error loading json obtained while listing Control Room workspaces.\n{e}",
            )
        for workspace_info in lst:
            permissions = workspace_info.get("permissions")
            if isinstance(permissions, dict):
                if not permissions.get("canReadRobots"):
                    log.info(
                        "Skipped workspace: %s (no canReadRobots permissions).",
                        workspace_info,
                    )
                    continue

            ret.append(
                RccWorkspace(
                    workspace_id=workspace_info["id"],
                    workspace_name=workspace_info["name"],
                    organization_name=workspace_info.get(
                        "orgName", "<Unable to get organization name>"
                    ),
                )
            )
        return ActionResult(True, None, ret)

    @implements(IRcc.cloud_list_workspace_robots)
    def cloud_list_workspace_robots(
        self, workspace_id: str
    ) -> ActionResult[List[IRccRobotMetadata]]:
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
                False,
                "Error listing Control Room workspace robots (output not available).",
            )

        try:
            workspace_info = json.loads(output)
        except Exception as e:
            log.exception(f"Error parsing json: {output}")
            return ActionResult(
                False,
                f"Error loading json obtained while listing Control Room workspaces activities.\n{e}",
            )

        if not isinstance(workspace_info, dict):
            log.critical(f"Expected dict as top-level from json: {output}")
            msg = f"Unexpected type of Control Room workspace activity json (expected dict, found: {type(workspace_info)}"
            return ActionResult(False, msg)

        for activity_info in workspace_info.get("activities", []):
            try:
                robot_id = activity_info["id"]
                robot_name = activity_info["name"]
            except:
                log.critical(
                    f"Error getting robot id/name from {args}:\nOutput:\n{output}"
                )
                continue

            if robot_id is None:
                log.critical(f"Robot id not available in {args}:\nOutput:\n{output}")
                continue

            if robot_name is None:
                log.critical(f"Robot name not available in {args}:\nOutput:\n{output}")
                robot_name = "Robot name unavailable"

            ret.append(RccRobotMetadata(robot_id=robot_id, robot_name=robot_name))
        return ActionResult(True, None, ret)

    @implements(IRcc.cloud_set_robot_contents)
    def cloud_set_robot_contents(
        self, directory: str, workspace_id: str, robot_id: str
    ) -> ActionResult:
        if not os.path.exists(directory):
            return ActionResult(
                False, f"Expected: {directory} to exist to upload to the Control Room."
            )
        if not os.path.isdir(directory):
            return ActionResult(
                False,
                f"Expected: {directory} to be a directory to upload to the Control Room.",
            )

        args = ["cloud", "push"]
        args.extend(["--directory", directory])
        args.extend(["--workspace", workspace_id])
        args.extend(["--robot", robot_id])

        args = self._add_config_to_args(args)
        error_action_result = self._add_account_to_args(args)
        if error_action_result is not None:
            return error_action_result

        ret = self._run_rcc(args, mutex_name=RCC_CLOUD_ROBOT_MUTEX_NAME, timeout=60 * 5)
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
            args,
            mutex_name=RCC_CLOUD_ROBOT_MUTEX_NAME,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        if not ret.success:
            return ret

        try:
            # Note: result is the package id.
            stdout = ret.result
            if not stdout:
                return ActionResult(
                    False, f"No process stdout when creating new Control Room package."
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

    @implements(IRcc.get_robot_yaml_env_info)
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
        from robocorp_code.holetree_manager import HolotreeManager
        from robocorp_code.rcc_space_info import format_conda_contents_to_compare

        if holotree_manager is None:
            holotree_manager = HolotreeManager(self)

        formatted_conda_yaml_contents = format_conda_contents_to_compare(
            conda_yaml_contents
        )

        broken_action_result = self.broken_conda_configs.get(
            formatted_conda_yaml_contents
        )

        if broken_action_result is not None:
            msg = f"Environment from previously broken {conda_yaml_path.name} requested: {conda_yaml_path}.\n-- VSCode restart required to retry."
            log.critical(msg)
            return ActionResult(False, msg, None)

        space_info: RCCSpaceInfo = holotree_manager.compute_valid_space_info(
            conda_yaml_path, conda_yaml_contents
        )

        environ: Dict[str, str]

        proceed_to_create_env = False
        with space_info.acquire_lock():
            space_state = SpaceState(space_info.state_path.read_text("utf-8"))
            if space_state == SpaceState.CREATED:
                space_info.requested_pid_path.write_text(str(os.getpid()))
                space_info.state_path.write_text(
                    SpaceState.ENV_REQUESTED.value, "utf-8"
                )
                proceed_to_create_env = True

        if space_state in (SpaceState.ENV_REQUESTED, SpaceState.ENV_READY):
            # Someone has already requested this state to be created, let's
            # wait for it.
            timeout = 60 * 60  # Wait up to 1 hour for the env...
            timeout_at = time.time() + timeout
            failures = 0
            while time.time() < timeout_at:
                try:
                    space_state = SpaceState(space_info.state_path.read_text("utf-8"))
                    if space_state == SpaceState.ENV_REQUESTED:
                        pid = space_info.load_requested_pid()
                        if not pid or not is_process_alive(int(pid)):
                            with space_info.acquire_lock():
                                # Check again with a lock in place. If it's still not valid (the
                                # pid could've exited and not finished its job), we'll become the
                                # space creators ourselves.
                                space_state = SpaceState(
                                    space_info.state_path.read_text("utf-8")
                                )
                                if space_state == SpaceState.ENV_REQUESTED:
                                    pid = space_info.load_requested_pid()
                                    if not pid or not is_process_alive(int(pid)):
                                        space_info.requested_pid_path.write_text(
                                            str(os.getpid())
                                        )
                                        proceed_to_create_env = True
                                        break

                    if space_state == SpaceState.ENV_READY:
                        with space_info.acquire_lock():
                            environ = json.loads(
                                space_info.env_json_path.read_text("utf-8", "replace")
                            )
                            space_info.update_last_usage()

                        if env_json_path:
                            try:
                                env_json_contents = json.loads(
                                    env_json_path.read_text("utf-8", "replace")
                                )
                                environ.update(env_json_contents)
                            except:
                                log.exception(
                                    f"Unable to load environment information from {env_json_path}."
                                )

                        if not isinstance(environ, dict):
                            try:
                                raise RuntimeError(
                                    f"Expected environment to be a dict. Found: {type(environ)}"
                                )
                            except RuntimeError as e:
                                log.exception()
                                proceed_to_create_env = True
                                break

                        new_env = {}
                        for key, val in environ.items():
                            # Just making sure we have a Dict[str, str]
                            new_env[str(key)] = str(val)

                        return ActionResult(
                            True, None, RobotInfoEnv(new_env, space_info)
                        )
                except Exception:
                    log.exception(
                        "Error when waiting for space_info creation to finish (handled and still waiting)."
                    )
                    failures += 1

                if failures > 5:
                    return ActionResult(
                        False,
                        f"Unable to get environment for space_info: {space_info.space_name}. Unable to collect env.",
                        None,
                    )
                time.sleep(2)

            if not proceed_to_create_env:
                return ActionResult(
                    False,
                    f"Environment for space_info: {space_info.space_name} not ready after waiting for {timeout/60} minutes.",
                    None,
                )

        # It was just created, let's get the env info and save it as needed.
        def return_failure(msg: Optional[str]) -> ActionResult[IRobotYamlEnvInfo]:
            log.critical(
                (
                    "Unable to create environment from:\n%s\n"
                    "To recreate the environment, please change the related conda yaml\n"
                    "or restart VSCode to retry with the same conda yaml contents."
                ),
                conda_yaml_path,
            )

            if not msg:
                msg = "<unknown reason>"
            log.critical(msg)
            action_result: ActionResult[IRobotYamlEnvInfo] = ActionResult(
                False, msg, None
            )

            self.broken_conda_configs[formatted_conda_yaml_contents] = action_result

            with space_info.acquire_lock():
                # If some failure happened, mark this as just created (so, it
                # can be reused).
                # But still, mark this conda yaml explicitly as invalid (i.e.:
                # it's expected that trying to resolve it again won't work, so,
                # the user must either restart vscode or change the conda yaml
                # for it to be requested again).
                space_info.state_path.write_text(SpaceState.CREATED.value, "utf-8")

            return action_result

        args = [
            "holotree",
            "variables",
            "--space",
            space_info.space_name,
            str(conda_yaml_path),
        ]
        args.append("--json")
        args.append("--no-retry-build")
        args.append("--no-pyc-management")
        try:
            sys.stderr.write(
                f"Collecting environment info for {conda_yaml_path} in space: {space_info.space_name}\n"
            )
            ret = self._run_rcc(
                args,
                mutex_name=RCC_CLOUD_ROBOT_MUTEX_NAME,
                cwd=str(robot_yaml_path.parent),
                timeout=timeout,  # Creating the env may be really slow!
                show_interactive_output=True,
            )

            if not ret.success:
                if on_env_creation_error is not None:
                    on_env_creation_error(ret)
                return return_failure(ret.message)

            contents: Optional[str] = ret.result
            if not contents:
                return return_failure("Unable to get output when getting environment.")

            environ = {}
            for entry in json.loads(contents):
                key = str(entry["key"])
                value = str(entry["value"])
                if key:
                    environ[key] = value

            if "CONDA_PREFIX" not in environ:
                msg = f"Did not find CONDA_PREFIX in {environ}"
                return return_failure(msg)

            if "PYTHON_EXE" not in environ:
                msg = f"Did not find PYTHON_EXE in {environ}"
                return return_failure(msg)

            with space_info.acquire_lock():
                space_info.env_json_path.write_text(json.dumps(environ), "utf-8")
                space_info.state_path.write_text(SpaceState.ENV_READY.value, "utf-8")
                try:
                    os.remove(space_info.damaged_path)
                except:
                    pass
                space_info.update_last_usage()

            if not space_info.conda_prefix_identity_yaml_still_matches_cached_space():
                return return_failure(
                    "Right after creating env, the environment does NOT match the conda yaml!"
                )

            if env_json_path:
                try:
                    env_json_contents = json.loads(
                        env_json_path.read_text("utf-8", "replace")
                    )
                    for key, val in env_json_contents.items():
                        environ[str(key)] = str(val)
                except:
                    log.exception(f"Error loading json from: {env_json_path}")

            return ActionResult(True, None, RobotInfoEnv(environ, space_info))
        except Exception as e:
            log.exception("Error creating environment from: %s", conda_yaml_path)
            return return_failure(str(e))

    @implements(IRcc.check_conda_installed)
    def check_conda_installed(self, timeout=None) -> ActionResult[str]:
        # With mamba this is not needed anymore.
        # Note: api kept just for backward compatibility.
        return ActionResult(success=True, message=None, result="OK.")

    @implements(IRcc.feedack_metric)
    def feedack_metric(self, name, value="+1") -> ActionResult[str]:
        key = f"{name}.{value}"
        if key in self._feedback_metrics_reported:
            return ActionResult(True)

        self._feedback_metrics_reported.add(key)

        return self._run_rcc(
            ["feedback", "metric", "-t", "vscode", "-n", name, "-v", value],
            mutex_name=None,
            log_errors=False,
        )

    def configuration_diagnostics(self, robot_yaml, json=True) -> ActionResult[str]:
        return self._run_rcc(
            ["configuration", "diagnostics"]
            + (["--json"] if json else [])
            + ["-r", robot_yaml],
            mutex_name=None,
            timeout=60,
        )

    def configuration_settings(self) -> ActionResult[str]:
        return self._run_rcc(
            ["configuration", "settings", "--json"],
            mutex_name=None,
            timeout=60,
        )

    def holotree_import(self, zip_file: Path, enable_shared: bool) -> ActionResult[str]:
        if enable_shared:
            result = self._run_rcc(
                ["holotree", "shared", "--enable", "--once"],
                mutex_name=None,
                timeout=60,
            )

            if not result.success:
                return result

            result = self._run_rcc(
                ["holotree", "init"],
                mutex_name=None,
                timeout=60,
            )

            if not result.success:
                return result

        return self._run_rcc(
            ["holotree", "import", str(zip_file)],
            mutex_name=None,
            timeout=500,
        )

    def holotree_variables(
        self, conda_yaml: Path, space_name: str, no_build: bool
    ) -> ActionResult[str]:
        args = ["holotree", "variables", "--space", space_name, "--json"]
        if no_build:
            args.append("--no-build")
        args.append(str(conda_yaml))
        return self._run_rcc(
            args,
            mutex_name=None,
            timeout=500,
        )

    def __typecheckself__(self) -> None:
        _: IRcc = check_implements(self)


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

    from robocorp_code.path_operations import (
        LOCK_TIMEOUT,
        get_user,
        make_numbered_dir_with_cleanup,
    )

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
