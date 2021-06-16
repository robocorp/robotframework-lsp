import argparse
import sys
import os
import traceback

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

LOG_FORMAT = "%(asctime)s UTC pid: %(process)d - %(threadName)s - %(levelname)s - %(name)s\n%(message)s\n\n"

_critical_error_log_file = os.path.join(
    os.path.expanduser("~"), "robotframework_interactive_critical.log"
)


def _critical_msg(msg):
    with open(_critical_error_log_file, "a+") as stream:
        stream.write(msg + "\n")


def add_arguments(parser):
    class DefaultOptions(object):
        verbose = 0

    parser.description = "RobotFramework Interactive"

    parser.add_argument(
        "--tcp", action="store_true", help="Use TCP client instead of stdio."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Connect to this IP address (i.e.: 127.0.0.01).",
    )
    parser.add_argument(
        "--port", type=int, default=-1, help="Connect to this port (i.e.: 1456)."
    )

    parser.add_argument(
        "--log-file",
        help="Redirect logs to the given file instead of writing to stderr (i.e.: c:/temp/my_log.log).",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=DefaultOptions.verbose,
        help="Increase verbosity of log output (i.e.: -vv).",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="If passed, just prints the version to the standard output and exits.",
    )


def main(args=None, language_server_class=None):
    original_args = args if args is not None else sys.argv[1:]

    parser = argparse.ArgumentParser()
    add_arguments(parser)

    args = parser.parse_args(args=original_args)
    verbose = args.verbose
    log_file = args.log_file or ""

    try:
        try:
            import robotframework_interactive
        except ImportError:
            # Automatically add it to the path if __main__ is being executed.
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import robotframework_interactive  # @UnusedImport
        robotframework_interactive.import_robocorp_ls_core()

        from robocorp_ls_core.robotframework_log import (
            configure_logger,
            log_args_and_python,
            get_logger,
        )
    except:
        # Failed before having setup the logger (but after reading args).
        log_file = os.path.expanduser(log_file)
        log_file = os.path.realpath(os.path.abspath(log_file))
        dirname = os.path.dirname(log_file)
        basename = os.path.basename(log_file)
        try:
            os.makedirs(dirname)
        except:
            pass  # Ignore error if it already exists.

        name, ext = os.path.splitext(basename)
        postfix = "rf_interactive.init"
        log_file = os.path.join(
            dirname, name + "." + postfix + "." + str(os.getpid()) + ext
        )
        with open(log_file, "a+") as stream:
            traceback.print_exc(file=stream)

        raise

    if args.version:
        sys.stdout.write(robotframework_interactive.__version__)
        sys.stdout.flush()
        return

    configure_logger("rfinteractive", verbose, log_file)
    log = get_logger("robotframework_interactive.__main__")
    log_args_and_python(log, original_args, robotframework_interactive)

    try:
        from robotframework_interactive.server.options import Setup, Options

        Setup.options = Options(args)

        # Ok, now that we have our options, let's connect back.

        from robocorp_ls_core.python_ls import (
            start_io_lang_server,
            start_tcp_lang_client,
            binary_stdio,
        )

        if args.tcp:
            start_tcp_lang_client(args.host, args.port, language_server_class)
        else:
            stdin, stdout = binary_stdio()
            start_io_lang_server(stdin, stdout, language_server_class)

    except:
        log.exception("Error initializing")
        raise


if __name__ == "__main__":
    try:
        if sys.version_info[0] <= 2:
            raise AssertionError(
                "Python 3+ is required for RobotFramework Interactive.\nCurrent executable: "
                + sys.executable
            )
        main()
    except (SystemExit, KeyboardInterrupt):
        pass
    except:
        # Critical error (the logging may not be set up properly).
        # Print to file and stderr.
        with open(_critical_error_log_file, "a+") as stream:
            traceback.print_exc(file=stream)

        traceback.print_exc()
