from subprocess import CalledProcessError
import sys
from typing import Optional, List, Any
import weakref

from robocorp_ls_core.basic import implements, as_str
from robocorp_ls_core.constants import NULL
from robocorp_ls_core.protocols import IConfig, IConfigProvider
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_code.protocols import (
    IRcc,
    IRccWorkspace,
    IRccActivity,
    ActionResult,
    typecheck_ircc,
    typecheck_ircc_workspace,
    typecheck_ircc_activity,
)
from pathlib import Path
import os.path


log = get_logger(__name__)

RCC_CLOUD_ACTIVITY_MUTEX_NAME = "rcc_cloud_activity"
RCC_CREDENTIALS_MUTEX_NAME = "rcc_credentials"


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
                        url = (
                            "https://downloads.code.robocorp.com/rcc/windows64/rcc.exe"
                        )
                    else:
                        url = (
                            "https://downloads.code.robocorp.com/rcc/windows32/rcc.exe"
                        )

                elif sys.platform == "darwin":
                    url = "https://downloads.code.robocorp.com/rcc/macos64/rcc"

                else:
                    if is_64:
                        url = "https://downloads.code.robocorp.com/rcc/linux64/rcc"
                    else:
                        url = "https://downloads.code.robocorp.com/rcc/linux32/rcc"

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


@typecheck_ircc_activity
class RccActivity(object):
    def __init__(self, activity_id: str, activity_name: str):
        self._activity_id = activity_id
        self._activity_name = activity_name

    @property
    def activity_id(self) -> str:
        return self._activity_id

    @property
    def activity_name(self) -> str:
        return self._activity_name


@typecheck_ircc_workspace
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


@typecheck_ircc
class Rcc(object):
    def __init__(self, config_provider: IConfigProvider) -> None:
        self._config_provider = weakref.ref(config_provider)

        self.credentials: Optional[str] = None

    def _get_str_optional_setting(self, setting_name) -> Any:
        config_provider = self._config_provider()
        config: Optional[IConfig] = None
        if config_provider is not None:
            config = config_provider.config

        if config:
            return config.get_setting(setting_name, str, None)
        return None

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
        expect_ok=True,
        error_msg: str = "",
        mutex_name=None,
        cwd: Optional[str] = None,
    ) -> ActionResult[str]:
        """
        Returns an ActionResult where the result is the stdout of the executed command.
        """
        from robocorp_ls_core.basic import build_subprocess_kwargs
        from subprocess import check_output
        from robocorp_ls_core.subprocess_wrapper import subprocess

        rcc_location = self.get_rcc_location()

        env = os.environ.copy()
        env.pop("PYTHONPATH", "")
        env.pop("PYTHONHOME", "")
        env.pop("VIRTUAL_ENV", "")
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        kwargs: dict = build_subprocess_kwargs(cwd, env, stderr=subprocess.PIPE)
        args = [rcc_location] + args
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
            msg = f"Error running: {cmdline}.\nStdout: {stdout}\nStderr: {stderr}"
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

        log.debug(f"Output from: {cmdline}:\n{output}")
        if expect_ok:
            if "OK." in output:
                return ActionResult(success=True, message=None, result=output)
        else:
            return ActionResult(success=True, message=None, result=output)

        return ActionResult(
            success=False, message="OK. not found in message", result=output
        )

    @implements(IRcc.get_template_names)
    def get_template_names(self) -> ActionResult[List[str]]:
        result = self._run_rcc("activity initialize -l".split())
        if not result.success:
            return ActionResult(success=False, message=result.message)

        output = result.result
        if output is None:
            return ActionResult(success=False, message="Output not available")
        templates = []
        for line in output.splitlines():
            if line.startswith("- "):
                template_name = line[2:].strip()
                templates.append(template_name)

        return ActionResult(success=True, message=None, result=sorted(templates))

    def _add_config_to_args(self, args: List[str]) -> List[str]:
        config_location = self.config_location
        if config_location:
            args.append("--config")
            args.append(config_location)
        return args

    @implements(IRcc.create_activity)
    def create_activity(self, template: str, directory: str) -> ActionResult:
        args = ["activity", "initialize", "-t", template, "-d", directory]
        args = self._add_config_to_args(args)
        return self._run_rcc(args, error_msg="Error creating activity.")

    @implements(IRcc.add_credentials)
    def add_credentials(self, credential: str) -> ActionResult:
        args = ["config", "credentials"]
        endpoint = self.endpoint
        if endpoint:
            args.append("--endpoint")
            args.append(endpoint)

        args = self._add_config_to_args(args)

        args.append(credential)

        return self._run_rcc(args, mutex_name=RCC_CREDENTIALS_MUTEX_NAME)

    @implements(IRcc.credentials_valid)
    def credentials_valid(self) -> bool:
        import json

        args = ["config", "credentials", "-j", "--verified"]
        endpoint = self.endpoint
        if endpoint:
            args.append("--endpoint")
            args.append(endpoint)

        args = self._add_config_to_args(args)

        result = self._run_rcc(
            args, expect_ok=False, mutex_name=RCC_CREDENTIALS_MUTEX_NAME
        )
        if not result.success:
            msg = f"Error checking credentials: {result.message}"
            log.critical(msg)
            return False

        output = result.result
        if not output:
            msg = f"Error. Expected to get info on credentials (found no output)."
            log.critical(msg)
            return False

        for credential in json.loads(output):
            timestamp = credential.get("verified")
            if timestamp and int(timestamp):
                return True
        # Found no valid credential
        return False

    @implements(IRcc.cloud_list_workspaces)
    def cloud_list_workspaces(self) -> ActionResult[List[IRccWorkspace]]:
        import json

        ret: List[IRccWorkspace] = []
        args = ["cloud", "workspace"]
        args = self._add_config_to_args(args)

        result = self._run_rcc(
            args, expect_ok=False, mutex_name=RCC_CLOUD_ACTIVITY_MUTEX_NAME
        )

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

    @implements(IRcc.cloud_list_workspace_activities)
    def cloud_list_workspace_activities(
        self, workspace_id: str
    ) -> ActionResult[List[IRccActivity]]:
        import json

        ret: List[IRccActivity] = []
        args = ["cloud", "workspace"]
        args.extend(("--workspace", workspace_id))
        args = self._add_config_to_args(args)
        result = self._run_rcc(
            args, expect_ok=False, mutex_name=RCC_CLOUD_ACTIVITY_MUTEX_NAME
        )
        if not result.success:
            return ActionResult(False, result.message)

        output = result.result
        if not output:
            return ActionResult(
                False,
                "Error listing cloud workspace activities (output not available).",
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
                RccActivity(
                    activity_id=activity_info["id"], activity_name=activity_info["name"]
                )
            )
        return ActionResult(True, None, ret)

    @implements(IRcc.cloud_set_activity_contents)
    def cloud_set_activity_contents(
        self, directory: str, workspace_id: str, package_id: str
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
        args.extend(["--package", package_id])

        args = self._add_config_to_args(args)
        ret = self._run_rcc(args, mutex_name=RCC_CLOUD_ACTIVITY_MUTEX_NAME)
        return ret

    @implements(IRcc.cloud_create_activity)
    def cloud_create_activity(
        self, workspace_id: str, package_name: str
    ) -> ActionResult[str]:
        args = ["cloud", "new"]
        args.extend(["--workspace", workspace_id])
        args.extend(["--package", package_name])

        args = self._add_config_to_args(args)
        ret = self._run_rcc(
            args, mutex_name=RCC_CLOUD_ACTIVITY_MUTEX_NAME, expect_ok=False
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
            # Created new activity package named 'New package' with identity 1414.
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
            log.exception("Error creating new activity package.")
            return ActionResult(
                False, f"Unable to extract package id from: {stdout}. Error: {e}"
            )

        return ActionResult(ret.success, None, package_id)

    def iter_package_yaml_activities(self, package_yaml_dict_contents: dict):
        activities = package_yaml_dict_contents.get("activities")
        if activities and isinstance(activities, dict):
            for activity_name, activity in activities.items():
                if isinstance(activity, dict):
                    yield activity_name, activity

    @implements(IRcc.run_python_code_package_yaml)
    def run_python_code_package_yaml(
        self,
        python_code: str,
        conda_yaml_str_contents: Optional[str],
        silent: bool = True,
        timeout=None,
    ) -> ActionResult[str]:
        from robocorp_ls_core import yaml_wrapper

        # The idea is obtaining a temporary directory, creating the needed
        # python file, package.yaml and conda file and then executing an activity
        # that'll execute the python file.
        directory = make_numbered_in_temp(lock_timeout=60 * 60)

        python_file: Path = directory / "code_to_exec.py"
        python_file.write_text(python_code, encoding="utf-8")

        # Note that the environ is not set (because the activityRoot cannot be
        # set to a non-relative directory copying the existing environ leads to
        # wrong results).
        package_yaml: Path = directory / "package.yaml"
        p: dict = {
            "activities": {
                "activity": {
                    "activityRoot": ".",
                    "output": ".",
                    "action": {"command": ["python", str(python_file)]},
                }
            }
        }
        if conda_yaml_str_contents:
            p["condaConfig"] = "conda.yaml"
            conda_file: Path = directory / "conda.yaml"
            conda_file.write_text(conda_yaml_str_contents, encoding="utf-8")

        package_yaml.write_text(yaml_wrapper.dumps(p), encoding="utf-8")

        args = ["activity", "run", "-p", str(package_yaml)]
        if silent:
            args.append("--silent")
        ret = self._run_rcc(
            args,
            mutex_name=RCC_CLOUD_ACTIVITY_MUTEX_NAME,
            expect_ok=False,
            cwd=str(directory),
            timeout=timeout,  # Creating the env may be really slow!
        )
        return ret

    @implements(IRcc.check_conda_installed)
    def check_conda_installed(self, timeout=None) -> ActionResult[str]:
        return self._run_rcc(
            ["conda", "check", "-i"],
            mutex_name=RCC_CLOUD_ACTIVITY_MUTEX_NAME,
            timeout=timeout,  # Creating the env may be really slow!
        )

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

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
