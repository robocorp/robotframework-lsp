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
try:
    import Queue as queue
except:
    import queue
import threading

import pytest
import sys
import os

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]


@pytest.fixture
def dap_logs_dir(tmpdir):
    logs_directory = tmpdir.join("logs_adapter")
    logs_directory.mkdir()
    yield logs_directory

    for name in os.listdir(str(logs_directory)):
        print("\n--- %s contents:" % (name,))
        with open(str(logs_directory.join(name)), "r") as stream:
            print(stream.read())


@pytest.fixture
def dap_log_file(dap_logs_dir):
    filename = str(dap_logs_dir.join("robotframework_dap_tests.log"))
    sys.stderr.write("Logging subprocess to: %s\n" % (filename,))

    yield filename


@pytest.fixture
def dap_process_stderr_file(dap_logs_dir):
    filename = str(dap_logs_dir.join("robotframework_dap_tests_stderr.log"))
    sys.stderr.write("Output subprocess stderr to: %s\n" % (filename,))
    with open(filename, "wb") as stream:
        yield stream

    for name in os.listdir(str(dap_logs_dir)):
        print("\n--- %s contents:" % (name,))
        with open(str(dap_logs_dir.join(name)), "r") as stream:
            print(stream.read())


@pytest.fixture
def dap_process(dap_log_file, dap_process_stderr_file):
    import subprocess
    from robotframework_debug_adapter import __main__
    from robocode_ls_core.basic import kill_process_and_subprocesses

    env = os.environ.copy()
    env["ROBOTFRAMEWORK_DAP_LOG_LEVEL"] = "3"
    env["ROBOTFRAMEWORK_DAP_LOG_FILENAME"] = dap_log_file

    dap_process = subprocess.Popen(
        [sys.executable, "-u", __main__.__file__],
        stdout=subprocess.PIPE,
        stderr=dap_process_stderr_file,
        stdin=subprocess.PIPE,
        env=env,
    )
    assert dap_process.returncode is None
    yield dap_process
    if dap_process.returncode is None:
        kill_process_and_subprocesses(dap_process.pid)


class _DebuggerAPI(object):
    def __init__(self, reader, writer, write_queue, read_queue):
        self.reader = reader
        self.writer = writer
        self.write_queue = write_queue
        self.read_queue = read_queue
        self.all_messages_read = []

    def write(self, msg):
        """
        :param BaseSchema msg:
            The message to be written.
        """
        self.write_queue.put(msg)

    def read(self, expect_class=None, accept_msg=None):
        """
        Waits for a message and returns it (may throw error if there's a timeout waiting for the message).
        """
        from robotframework_debug_adapter.dap.dap_schema import OutputEvent

        while True:
            msg = self.read_queue.get(timeout=5)
            if hasattr(msg, "to_dict"):
                sys.stderr.write("Read: %s\n\n" % (msg.to_dict(),))
            else:
                sys.stderr.write("Read: %s\n\n" % (msg,))
            self.all_messages_read.append(msg)
            if expect_class is not None or accept_msg is not None:
                if self._matches(msg, expect_class, accept_msg):
                    return msg

                # Only skip OutputEvent. Other events must match.
                if not isinstance(msg, OutputEvent):
                    raise AssertionError(
                        "Received: %s when expecting: %s" % (msg, expect_class)
                    )

            else:
                # expect_class and accept_msg are None
                return msg

        return msg

    def assert_message_found(self, expect_class=None, accept_msg=None):
        for msg in self.all_messages_read:
            if self._matches(msg, expect_class, accept_msg):
                return True
        return False

    def _matches(self, msg, expect_class=None, accept_msg=None):
        if (expect_class is None or isinstance(msg, expect_class)) and (
            accept_msg is None or accept_msg(msg)
        ):
            return True
        return False

    def get_dap_case_file(self, filename, must_exist=True):
        import os.path

        ret = os.path.join(os.path.dirname(__file__), "_dap_resources", filename)
        if must_exist:
            assert os.path.exists(ret), "%s does not exist." % (ret,)

        return ret


@pytest.fixture
def debugger_api(dap_process):

    from robotframework_debug_adapter.debug_adapter_threads import writer_thread
    from robotframework_debug_adapter.debug_adapter_threads import reader_thread

    write_to = dap_process.stdin
    read_from = dap_process.stdout

    write_queue = queue.Queue()
    read_queue = queue.Queue()

    writer = threading.Thread(target=writer_thread, args=(write_to, write_queue))
    writer.daemon = True
    reader = threading.Thread(
        target=reader_thread, args=(read_from, read_queue.put, write_queue)
    )
    reader.daemon = True

    reader.start()
    writer.start()

    return _DebuggerAPI(
        reader=reader, writer=writer, write_queue=write_queue, read_queue=read_queue
    )
