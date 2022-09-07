# Original work Copyright 2017 Palantir Technologies, Inc. (MIT)
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Robocorp Technologies Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import sys
import os


__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

LOG_FORMAT = "%(asctime)s UTC pid: %(process)d - %(threadName)s - %(levelname)s - %(name)s\n%(message)s\n\n"

_critical_error_log_file = os.path.join(
    os.path.expanduser("~"), "robotframework_ls_critical.log"
)


def _critical_msg(msg):
    with open(_critical_error_log_file, "a+") as stream:
        stream.write(msg + "\n")


def add_arguments(parser):
    from robotframework_ls.options import Options

    parser.description = "RobotFramework Language Server"

    parser.add_argument(
        "--tcp", action="store_true", help="Use TCP server instead of stdio."
    )
    parser.add_argument(
        "--host",
        default=Options.host,
        help="Bind to this IP address (i.e.: 127.0.0.01).",
    )
    parser.add_argument(
        "--port", type=int, default=Options.port, help="Bind to this port (i.e.: 1456)."
    )

    parser.add_argument(
        "--log-file",
        help="Redirect logs to the given file instead of writing to stderr (i.e.: c:/temp/my_log.log).",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=Options.verbose,
        help="Increase verbosity of log output (i.e.: -vv).",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="If passed, just prints the version to the standard output and exits.",
    )


def main(
    args=None,
    after_bind=lambda server: None,
    language_server_class=None,
    log_prefix="lsp",
):
    original_args = args if args is not None else sys.argv[1:]

    try:
        import robotframework_ls
    except ImportError:
        # Automatically add it to the path if __main__ is being executed.
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import robotframework_ls  # @UnusedImport
    robotframework_ls.import_robocorp_ls_core()

    from robotframework_ls.options import Setup, Options
    from robocorp_ls_core.robotframework_log import (
        configure_logger,
        log_args_and_python,
        get_logger,
    )

    from robocorp_ls_core.python_ls import (
        start_io_lang_server,
        start_tcp_lang_server,
        binary_stdio,
    )

    verify_robot_imports = False
    if language_server_class is None:
        from robotframework_ls.robotframework_ls_impl import (
            RobotFrameworkLanguageServer,
        )

        language_server_class = RobotFrameworkLanguageServer
        verify_robot_imports = True

    parser = argparse.ArgumentParser()
    add_arguments(parser)

    args = parser.parse_args(args=original_args)
    if args.version:
        sys.stdout.write(robotframework_ls.__version__)
        sys.stdout.flush()
        return
    Setup.options = Options(args)
    verbose = args.verbose
    log_file = args.log_file or ""

    if not log_file:
        # If not specified in args, also check the environment variables.
        log_file = os.environ.get("ROBOTFRAMEWORK_LS_LOG_FILE", "")
        if log_file:
            # If the log file comes from the environment, make sure the log-level
            # also comes from it (with a log-level==2 by default).
            Setup.options.log_file = log_file
            try:
                verbose = int(os.environ.get("ROBOTFRAMEWORK_LS_LOG_LEVEL", "2"))
            except:
                verbose = 2
            Setup.options.verbose = verbose

    configure_logger(log_prefix, verbose, log_file)
    log = get_logger("robotframework_ls.__main__")
    log_args_and_python(log, original_args, robotframework_ls)

    if args.tcp:
        start_tcp_lang_server(
            args.host, args.port, language_server_class, after_bind=after_bind
        )
    else:
        if verify_robot_imports:
            # We just add the verification in the stdio mode (because the tcp is
            # used in tests where we start it as a thread).

            # "robot" should only be imported in the subprocess which is spawned
            # specifically for that robot framework version (we should only
            # parse the AST at those subprocesses -- if the import is done at
            # the main process something needs to be re-engineered to forward
            # the request to a subprocess).
            from robocorp_ls_core.basic import notify_about_import

            notify_about_import("robot")

        stdin, stdout = binary_stdio()
        start_io_lang_server(stdin, stdout, language_server_class)


if __name__ == "__main__":
    try:
        if sys.version_info[0] <= 2:
            raise AssertionError(
                "Python 3+ is required for the RobotFramework Language Server.\nCurrent executable: "
                + sys.executable
            )
        main()
    except (SystemExit, KeyboardInterrupt):
        pass
    except:
        # Critical error (the logging may not be set up properly).
        import traceback

        # Print to file and stderr.
        with open(_critical_error_log_file, "a+") as stream:
            traceback.print_exc(file=stream)

        traceback.print_exc()
