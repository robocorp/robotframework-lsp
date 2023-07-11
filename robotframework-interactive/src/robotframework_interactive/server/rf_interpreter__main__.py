import os.path
import traceback
import sys

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

_critical_error_log_file = os.path.join(
    os.path.expanduser("~"), "rf_interpreter_server_api_critical.log"
)


def _stderr_reader(stream):
    from robocorp_ls_core.robotframework_log import get_logger

    log = get_logger(__name__)

    try:
        while True:
            line = stream.readline()
            if not line:
                break
            sys.stderr.buffer.write(line)
    except:
        log.exception("Error reading from server api process stream.")
    finally:
        log.debug("Finished reading from server api process stream.")


def start_server_process(args=(), python_exe=None, env=None, cwd=None):
    """
    Calls this __main__ in another process.

    :param args:
        The list of arguments for the server process.
        i.e.:
            ["-vv", "--log-file=%s" % log_file]
    """
    from robocorp_ls_core.robotframework_log import get_logger
    from robocorp_ls_core.subprocess_wrapper import subprocess
    import threading

    log = get_logger(__name__)

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

    language_server_process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        env=environ,
        bufsize=0,
        cwd=cwd,
    )

    t = threading.Thread(target=_stderr_reader, args=(language_server_process.stderr,))
    t.name = "Stderr from RfInteractiveServerAPI (%s)" % (args,)
    t.daemon = True
    t.start()

    return language_server_process


def main():
    log = None
    try:
        try:
            import robotframework_interactive
        except ImportError:
            # Automatically add it to the path if __main__ is being executed.
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            import robotframework_interactive  # @UnusedImport
        robotframework_interactive.import_robocorp_ls_core()

        from robocorp_ls_core.robotframework_log import get_logger

        log = get_logger(__name__)

        log.info("Initializing RfInterpreter Server api. Args: %s", (sys.argv[1:],))

        from robotframework_interactive import __main__
        from robotframework_interactive.server.rf_interpreter_server_api import (
            RfInterpreterServerApi,
        )

        __main__.main(language_server_class=RfInterpreterServerApi)
    except:
        try:
            if log is not None:
                log.exception("Error initializing RfInterpreterServerApi.")
        finally:
            # Critical error (the logging may not be set up properly).

            # Print to file and stderr.
            with open(_critical_error_log_file, "a+") as stream:
                traceback.print_exc(file=stream)

            traceback.print_exc()


if __name__ == "__main__":
    main()
