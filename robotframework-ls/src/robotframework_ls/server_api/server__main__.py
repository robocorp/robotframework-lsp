import os.path
import traceback
import sys

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

_critical_error_log_file = os.path.join(
    os.path.expanduser("~"), "robotframework_server_api_critical.log"
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


def start_server_process(args=(), python_exe=None, env=None):
    """
    Calls this __main__ in another process.

    :param args:
        The list of arguments for the server process.
        i.e.:
            ["-vv", "--log-file=%s" % log_file, "--remote-fs-observer-port=23456"]
    """
    from robocorp_ls_core.robotframework_log import get_logger
    from robocorp_ls_core.subprocess_wrapper import subprocess
    import threading
    from robotframework_ls.options import Setup

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

    env_log = ["Environ:"]
    for key, val in environ.items():
        env_log.append("  %s=%s" % (key, val))

    if Setup.options.DEBUG_PROCESS_ENVIRON:
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
    t.name = "Stderr from ServerAPI (%s)" % (args,)
    t.daemon = True
    t.start()

    return language_server_process


def main():
    log = None
    try:
        src_folder = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        try:
            import robotframework_ls
        except ImportError:
            # Automatically add it to the path if __main__ is being executed.
            assert os.path.exists(src_folder), "Expected: %s to exist" % (src_folder,)
            sys.path.append(src_folder)
            import robotframework_ls  # @UnusedImport

        robotframework_ls.import_robocorp_ls_core()

        from robocorp_ls_core.robotframework_log import get_logger

        log = get_logger(__name__)

        log.info("Initializing RobotFramework Server api. Args: %s", (sys.argv[1:],))

        from robotframework_ls import __main__

        args = sys.argv[1:]
        new_args = []

        found_remote_fs_obverver_port = False
        from robocorp_ls_core.remote_fs_observer_impl import RemoteFSObserver

        observer = RemoteFSObserver("<unused>", extensions=None)

        pre_generate_libspecs = False
        index_workspace = False
        collect_tests = False

        for arg in args:
            if arg.startswith("--remote-fs-observer-port="):
                # Now, in this process, we don't own the RemoteFSObserver, we
                # just expect to connect to an existing one.
                found_remote_fs_obverver_port = True
                port = int(arg.split("=")[1].strip())

                observer.connect_to_server(port)

            elif arg == "--pre-generate-libspecs":
                pre_generate_libspecs = True

            elif arg == "--index-workspace":
                index_workspace = True

            elif arg == "--collect-tests":
                collect_tests = True

            else:
                new_args.append(arg)

        if not found_remote_fs_obverver_port:
            raise RuntimeError(
                'Expected "--remote-fs-observer-port=" to be passed in the arguments.'
            )

        from robotframework_ls.server_api.server import RobotFrameworkServerApi

        class RobotFrameworkServerApiWithObserver(RobotFrameworkServerApi):
            def __init__(self, *args, **kwargs):
                kwargs["observer"] = observer
                kwargs["pre_generate_libspecs"] = pre_generate_libspecs
                kwargs["index_workspace"] = index_workspace
                kwargs["collect_tests"] = collect_tests
                RobotFrameworkServerApi.__init__(self, *args, **kwargs)

        __main__.main(
            language_server_class=RobotFrameworkServerApiWithObserver,
            args=new_args,
            log_prefix="server-api",
        )
    except:
        try:
            if log is not None:
                log.exception("Error initializing RobotFrameworkServerApi.")
        finally:
            # Critical error (the logging may not be set up properly).

            # Print to file and stderr.
            with open(_critical_error_log_file, "a+") as stream:
                traceback.print_exc(file=stream)

            traceback.print_exc()


if __name__ == "__main__":
    main()
