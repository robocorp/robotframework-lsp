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

    log = None
    try:
        import sys

        try:
            import robotframework_debug_adapter
        except ImportError:
            # Automatically add it to the path if __main__ is being executed.
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import robotframework_debug_adapter  # @UnusedImport

        from robotframework_debug_adapter.debug_adapter_threads import (
            STOP_WRITER_THREAD,
        )
        from robotframework_ls.robotframework_log import (
            get_logger,
            configure_logger,
            log_args_and_python,
        )
        import traceback

        configure_logger("dap")
        log = get_logger("robotframework_debug_adapter.__main__")
        log_args_and_python(log, sys.argv)

        from robotframework_debug_adapter.debug_adapter_threads import reader_thread
        from robotframework_debug_adapter.debug_adapter_threads import writer_thread
        from robotframework_debug_adapter.command_processor import CommandProcessor

        try:
            from queue import Queue
        except ImportError:
            from Queue import Queue

        write_queue = Queue()
        command_processor = CommandProcessor(write_queue)

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
            args=(write_to, write_queue, "write to client"),
            name="Write to client",
        )
        reader = threading.Thread(
            target=reader_thread,
            args=(read_from, command_processor, write_queue, b"read from client"),
            name="Read from client",
        )

        reader.start()
        writer.start()

        reader.join()
        log.debug("Exited reader.\n")
        write_queue.put(STOP_WRITER_THREAD)
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


if __name__ == "__main__":
    main()
