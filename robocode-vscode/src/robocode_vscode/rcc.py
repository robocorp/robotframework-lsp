import sys
from robocode_ls_core.robotframework_log import get_logger
from robocode_ls_core.protocols import IConfig, ILanguageServer
from typing import Optional, List
import weakref

log = get_logger(__name__)


def download_rcc(location: str, force: bool = False) -> None:
    """
    Downloads rcc to the given location. Note that we don't overwrite it if it 
    already exists (unless force == True).
    
    :param location:
        The location to store the rcc executable in the filesystem.
    :param force:
        Whether we should overwrite an existing installation.
    """
    from robocode_ls_core.system_mutex import timed_acquire_mutex
    import os.path

    if not os.path.exists(location) or force:
        with timed_acquire_mutex("robocode_get_rcc", timeout=120):
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
    from robocode_vscode import get_extension_relative_path

    if sys.platform == "win32":
        location = get_extension_relative_path("bin", "rcc.exe")
    else:
        location = get_extension_relative_path("bin", "rcc")
    return location


class Rcc(object):
    def __init__(self, language_server):
        self._language_server = weakref.ref(language_server)

    def get_rcc_location(self) -> str:
        from robocode_vscode import settings
        import os.path

        language_server: ILanguageServer = self._language_server()
        config: Optional[IConfig] = None
        if language_server is not None:
            config = language_server.config

        rcc_location: str = ""
        if config:
            rcc_location = config.get_setting(settings.ROBOCODE_RCC_LOCATION, str)

        if not rcc_location:
            rcc_location = get_default_rcc_location()

        if not os.path.exists(rcc_location):
            download_rcc(rcc_location)
        return rcc_location

    def run(self, args: List[str], timeout: float = 30) -> str:
        from robocode_ls_core.basic import build_subprocess_kwargs
        from subprocess import check_output
        from robocode_ls_core.subprocess_wrapper import subprocess
        from subprocess import CalledProcessError

        rcc_location = self.get_rcc_location()

        cwd = None
        env = None
        kwargs: dict = build_subprocess_kwargs(cwd, env, stderr=subprocess.PIPE)
        args = [rcc_location] + args
        try:
            boutput: bytes = check_output(args, timeout=timeout, **kwargs)
        except CalledProcessError as e:
            log.exception("Error running: %s", args)
            log.critical("stderr: \n%s", e.stderr)
            raise
        except Exception:
            log.exception("Error running: %s", args)
            raise
        output = boutput.decode("utf-8", "replace")

        log.info(f"Output from: {args}:\n{output}")
        return output
