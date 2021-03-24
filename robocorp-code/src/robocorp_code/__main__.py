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
import traceback

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

LOG_FORMAT = "%(asctime)s UTC pid: %(process)d - %(threadName)s - %(levelname)s - %(name)s\n%(message)s\n\n"

_critical_error_log_file = os.path.join(
    os.path.expanduser("~"), "robocorp_code_critical.log"
)


def _critical_msg(msg):
    with open(_critical_error_log_file, "a+") as stream:
        stream.write(msg + "\n")


def add_arguments(parser):

    # Not using this import to be able to use this function before the pythonpath
    # is setup.
    # from robocorp_code.options import Options as DefaultOptions

    class DefaultOptions(object):
        host = "127.0.0.1"
        port = 1456
        verbose = 0

    parser.description = "Robocorp Code"

    parser.add_argument(
        "--tcp", action="store_true", help="Use TCP server instead of stdio."
    )
    parser.add_argument(
        "--host",
        default=DefaultOptions.host,
        help="Bind to this IP address (i.e.: 127.0.0.01).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DefaultOptions.port,
        help="Bind to this port (i.e.: 1456).",
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


def main(args=None, after_bind=lambda server: None, language_server_class=None):
    original_args = args if args is not None else sys.argv[1:]

    parser = argparse.ArgumentParser()
    add_arguments(parser)

    args = parser.parse_args(args=original_args)
    verbose = args.verbose
    log_file = args.log_file or ""

    try:
        try:
            import robocorp_code
        except ImportError:
            # Automatically add it to the path if __main__ is being executed.
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import robocorp_code  # @UnusedImport
        robocorp_code.import_robocorp_ls_core()

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
        postfix = "lsp.init"
        log_file = os.path.join(
            dirname, name + "." + postfix + "." + str(os.getpid()) + ext
        )
        with open(log_file, "a+") as stream:
            traceback.print_exc(file=stream)

        raise

    if args.version:
        sys.stdout.write(robocorp_code.__version__)
        sys.stdout.flush()
        return

    configure_logger("lsp", verbose, log_file)
    log = get_logger("robocorp_code.__main__")
    log_args_and_python(log, original_args, robocorp_code)

    try:
        from robocorp_code.options import Setup, Options

        Setup.options = Options(args)

        from robocorp_ls_core.python_ls import (
            start_io_lang_server,
            start_tcp_lang_server,
            binary_stdio,
        )

        if language_server_class is None:
            from robocorp_code.robocorp_language_server import RobocorpLanguageServer

            language_server_class = RobocorpLanguageServer

        if args.tcp:
            start_tcp_lang_server(
                args.host, args.port, language_server_class, after_bind=after_bind
            )
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
                "Python 3+ is required for Robocorp Code.\nCurrent executable: "
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
