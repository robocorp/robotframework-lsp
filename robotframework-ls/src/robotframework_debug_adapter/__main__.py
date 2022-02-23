"""
# Original work Copyright Fabio Zadrozny (EPL 1.0)
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
"""

import threading
import traceback
import os.path


__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]


_critical_error_log_file = os.path.join(
    os.path.expanduser("~"), "robotframework_dap_critical.log"
)


def main():
    """
    Starts the debug adapter (creates a thread to read from stdin and another to write to stdout as
    expected by the vscode debug protocol).

    We pass the command processor to the reader thread as the idea is that the reader thread will
    read a message, convert it to an instance of the message in the schema and then forward it to
    the command processor which will interpret and act on it, posting the results to the writer queue.
    """

    def close_logging_streams():
        pass

    log = None
    try:
        import sys

        if sys.version_info[0] <= 2:
            raise AssertionError(
                "Python 3+ is required for the RobotFramework Debug Adapter.\nCurrent executable: "
                + sys.executable
            )

        try:
            import robotframework_debug_adapter
            import robotframework_ls
        except ImportError:
            # Automatically add it to the path if __main__ is being executed.
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import robotframework_debug_adapter  # @UnusedImport
            import robotframework_ls

        robotframework_ls.import_robocorp_ls_core()

        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            STOP_WRITER_THREAD,
        )
        from robocorp_ls_core.robotframework_log import (
            get_logger,
            configure_logger,
            log_args_and_python,
            close_logging_streams,
        )

        from robotframework_debug_adapter.constants import LOG_FILENAME
        from robotframework_debug_adapter.constants import LOG_LEVEL

        configure_logger("dap", LOG_LEVEL, LOG_FILENAME)
        log = get_logger("robotframework_debug_adapter.__main__")
        log_args_and_python(log, sys.argv, robotframework_ls)

        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            reader_thread,
        )
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            writer_thread,
        )
        from robotframework_debug_adapter.debug_adapter_comm import DebugAdapterComm

        from queue import Queue

        to_client_queue = Queue()
        comm = DebugAdapterComm(to_client_queue)

        write_to = sys.stdout
        read_from = sys.stdin

        if sys.version_info[0] <= 2:
            if sys.platform == "win32":
                # must read streams as binary on windows
                import msvcrt

                msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        else:
            # Py3
            write_to = sys.stdout.buffer
            read_from = sys.stdin.buffer

        writer = threading.Thread(
            target=writer_thread,
            args=(write_to, to_client_queue, "write to client"),
            name="Write to client (dap __main__)",
        )
        reader = threading.Thread(
            target=reader_thread,
            args=(read_from, comm.from_client, to_client_queue, b"read from client"),
            name="Read from client (dap __main__)",
        )

        reader.start()
        writer.start()

        reader.join()
        log.debug("Exited reader.\n")
        to_client_queue.put(STOP_WRITER_THREAD)
        writer.join()
        log.debug("Exited writer.\n")
    except:
        if log is not None:
            log.exception("Error")
        # Critical error (the logging may not be set up properly).
        # Print to file and stderr.
        with open(_critical_error_log_file, "a+") as stream:
            traceback.print_exc(file=stream)

        traceback.print_exc()
    finally:
        if log is not None:
            log.debug("Exited main.\n")
        close_logging_streams()


if __name__ == "__main__":
    main()
