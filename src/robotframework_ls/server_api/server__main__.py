import logging
import os.path
import sys

__file__ = os.path.abspath(__file__)
log = logging.getLogger(__name__)

_critical_error_log_file = os.path.join(
    os.path.expanduser("~"), "robotframework_server_api_critical.log"
)


def _stderr_reader(stream):
    from robotframework_ls.constants import IS_PY2

    try:
        while True:
            line = stream.readline()
            if IS_PY2:
                sys.stderr.write(line)
            else:
                sys.stderr.buffer.write(line)
            if not line:
                break
    except:
        log.exception("Error reading from server api process stream.")
    finally:
        log.debug("Finished reading from server api process stream.")


def start_server_process(args=(), python_exe=None, env=None):
    """
    Calls this __main__ in another process.
    
    :param args:
        The list of arguments for the server process. 
        i.e.:
            ["-vv", "--log-file=%s" % log_file]
    """
    import subprocess
    import threading

    if python_exe:
        if not os.path.exists(python_exe):
            raise RuntimeError("Expected %s to exist" % (python_exe,))

    args = [python_exe or sys.executable, "-u", __file__] + list(args)
    log.debug('Starting server api process with args: "%s"' % ('" "'.join(args),))
    environ = os.environ.copy()
    environ.pop("PYTHONPATH", "")
    environ.pop("PYTHONHOME", "")
    environ.pop("VIRTUAL_ENV", "")
    if env is not None:
        for key, val in env.items():
            environ[key] = val

    environ["PYTHONIOENCODING"] = "utf-8"
    environ["PYTHONUNBUFFERED"] = "1"

    env_log = ["Environ:"]
    for key, val in environ.items():
        env_log.append("  %s=%s" % (key, val))

    log.debug("\n".join(env_log))

    language_server_process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        env=environ,
        bufsize=0,
    )

    t = threading.Thread(target=_stderr_reader, args=(language_server_process.stderr,))
    t.setName("Stderr from ServerAPI (%s)" % (args,))
    t.setDaemon(True)
    t.start()

    return language_server_process


if __name__ == "__main__":
    try:
        log.info("Initializing RobotFramework Server api. Args: %s", (sys.argv[1:],))

        try:
            import robotframework_ls
        except ImportError:
            # Automatically add it to the path if __main__ is being executed.
            sys.path.append(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )
            import robotframework_ls  # @UnusedImport

        from robotframework_ls import __main__
        from robotframework_ls.server_api.server import RobotFrameworkServerApi

        __main__.main(language_server_class=RobotFrameworkServerApi)
    except:
        # Critical error (the logging may not be set up properly).
        import traceback

        # Print to file and stderr.
        with open(_critical_error_log_file, "a+") as stream:
            traceback.print_exc(file=stream)

        traceback.print_exc()
