# coding: utf-8
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
import os
import queue
import sys
import threading
from typing import Iterable, Optional

import pytest  # type: ignore
from robocorp_ls_core.options import DEFAULT_TIMEOUT
from robocorp_ls_core.subprocess_wrapper import subprocess
from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]


@pytest.fixture
def dap_logs_dir(tmpdir):
    import locale

    logs_directory = tmpdir.join("logs_adapter")
    logs_directory.mkdir()
    yield logs_directory

    for name in os.listdir(str(logs_directory)):
        sys.stderr.write("\n--- %s contents:\n" % (name,))

        if name in ("output.xml", "report.html", "log.html"):
            sys.stderr.write("--- Not printed --- \n\n")
            continue

        with open(str(logs_directory.join(name)), "rb") as stream:
            contents = stream.read().decode(locale.getpreferredencoding(), "replace")
            sys.stderr.write(contents)
            sys.stderr.write("\n\n")


@pytest.fixture
def dap_log_file(dap_logs_dir):
    filename = str(dap_logs_dir.join("robocorp_code_dap_tests.log"))
    sys.stderr.write("Logging subprocess to: %s\n" % (filename,))

    yield filename


@pytest.fixture
def dap_process_stderr_file(dap_logs_dir):
    filename = str(dap_logs_dir.join("robocorp_code_dap_tests_stderr.log"))
    sys.stderr.write("Output subprocess stderr to: %s\n" % (filename,))
    with open(filename, "wb") as stream:
        yield stream


@pytest.fixture
def dap_process(dap_log_file, dap_process_stderr_file):
    from robocorp_ls_core.basic import kill_process_and_subprocesses

    from robocorp_code_debug_adapter import __main__

    env = os.environ.copy()
    env["ROBOCORP_CODE_DAP_LOG_LEVEL"] = "3"
    env["ROBOCORP_CODE_DAP_LOG_FILENAME"] = dap_log_file

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
    def __init__(
        self,
        reader=None,
        writer=None,
        write_queue=None,
        read_queue=None,
        dap_resources_dir=None,
    ):
        self.reader = reader
        self.writer = writer
        self.write_queue = write_queue
        self.read_queue = read_queue
        self.all_messages_read = []
        self.target = None
        self.dap_resources_dir = dap_resources_dir

    def write(self, msg):
        """
        :param BaseSchema msg:
            The message to be written.
        """
        self.write_queue.put(msg)
        return msg

    def read(self, expect_class=None, accept_msg=None, timeout=TIMEOUT):
        """
        Waits for a message and returns it (may throw error if there's a timeout waiting for the message).
        """
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEvent

        while True:
            msg = self.read_queue.get(timeout=timeout)
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
        raise AssertionError("Did not find expected message.")

    def _matches(self, msg, expect_class=None, accept_msg=None):
        if (expect_class is None or isinstance(msg, expect_class)) and (
            accept_msg is None or accept_msg(msg)
        ):
            return True
        return False

    def get_dap_case_file(self, filename, must_exist=True):
        import os.path

        ret = os.path.join(self.dap_resources_dir, filename)
        if must_exist:
            assert os.path.exists(ret), "%s does not exist." % (ret,)

        return ret

    def initialize(self, rcc_config_location):
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            InitializeRequest,
            InitializeRequestArguments,
            InitializeResponse,
        )

        self.write(
            InitializeRequest(
                InitializeRequestArguments(
                    adapterID="robocorp-code-adapter",
                    clientID="Stub",
                    clientName="stub",
                    locale="en-us",
                    linesStartAt1=True,
                    columnsStartAt1=True,
                    pathFormat="path",
                    supportsVariableType=True,
                    supportsVariablePaging=True,
                    supportsRunInTerminalRequest=True,
                    rccConfigLocation=rcc_config_location,
                )
            )
        )

        initialize_response = self.read(InitializeResponse)
        assert isinstance(initialize_response, InitializeResponse)
        assert initialize_response.request_seq == 0
        assert initialize_response.success
        assert initialize_response.command == "initialize"

    def configuration_done(self):
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            ConfigurationDoneRequest,
            ConfigurationDoneResponse,
        )

        self.write(ConfigurationDoneRequest())
        self.read(ConfigurationDoneResponse)

    def launch(
        self,
        robot,
        task,
        debug=False,
        success=True,
        terminal="none",
        args: Optional[Iterable[str]] = None,
        environ: Optional[dict] = None,
    ):
        """
        :param args:
            The arguments to the launch (for instance:
                ["--variable", "my_var:22"]
            )
        """
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            InitializedEvent,
            LaunchRequest,
            LaunchRequestArguments,
            LaunchResponse,
            Response,
        )

        launch_args = LaunchRequestArguments(
            __sessionId="some_id",
            noDebug=not debug,
            robot=robot,
            task=task,
            terminal=terminal,
        )
        if args:
            launch_args.kwargs["args"] = args
        if environ:
            launch_args.kwargs["env"] = environ
        self.write(LaunchRequest(launch_args))

        if success:
            # Initialized is sent just before the launch response (at which
            # point it's possible to send breakpoints).
            event = self.read(InitializedEvent, timeout=10 * 60)
            assert isinstance(event, InitializedEvent)

        if success:
            launch_response = self.read(LaunchResponse)
        else:
            launch_response = self.read(Response)
        assert launch_response.success == success

    def list_threads(self):
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import ThreadsRequest

        return self.wait_for_response(self.write(ThreadsRequest()))

    def set_breakpoints(self, target, lines):
        import os.path

        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            SetBreakpointsArguments,
            SetBreakpointsRequest,
            SetBreakpointsResponse,
            Source,
            SourceBreakpoint,
        )

        if isinstance(lines, int):
            lines = (lines,)
        assert isinstance(lines, (list, tuple))

        self.write(
            SetBreakpointsRequest(
                SetBreakpointsArguments(
                    source=Source(name=os.path.basename(target), path=target),
                    lines=lines,
                    breakpoints=[
                        SourceBreakpoint(line=line).to_dict() for line in lines
                    ],
                )
            )
        )
        response = self.read(SetBreakpointsResponse)
        assert len(response.body.breakpoints) == len(lines)

    def wait_for_response(self, request, response_class=None):
        from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import (
            get_response_class,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Response

        if response_class is None:
            response_class = get_response_class(request)

        def accept_message(response):
            if isinstance(request, dict):
                if response.request_seq == request["seq"]:
                    return True
            else:
                if response.request_seq == request.seq:
                    return True
            return False

        return self.read((response_class, Response), accept_message)


@pytest.fixture(scope="session")
def dap_resources_dir(tmpdir_factory):
    from robocorp_ls_core.copytree import copytree_dst_exists

    basename = "dap áéíóú"
    copy_to = str(tmpdir_factory.mktemp(basename))

    f = __file__
    original_resources_dir = os.path.join(os.path.dirname(f), "_dap_resources")
    assert os.path.exists(original_resources_dir)

    copytree_dst_exists(original_resources_dir, copy_to)
    resources_dir = copy_to
    assert os.path.exists(resources_dir)
    return resources_dir


@pytest.fixture
def debugger_api_core(dap_resources_dir):
    return _DebuggerAPI(dap_resources_dir=dap_resources_dir)


@pytest.fixture
def debugger_api(dap_process, dap_resources_dir):
    from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
        reader_thread,
        writer_thread,
    )

    write_to = dap_process.stdin
    read_from = dap_process.stdout

    write_queue = queue.Queue()
    read_queue = queue.Queue()

    writer = threading.Thread(
        target=writer_thread, args=(write_to, write_queue), name="Debugger API writer"
    )
    writer.daemon = True
    reader = threading.Thread(
        target=reader_thread,
        args=(read_from, read_queue.put, read_queue),
        name="Debugger API reader",
    )
    reader.daemon = True

    reader.start()
    writer.start()

    return _DebuggerAPI(
        reader=reader,
        writer=writer,
        write_queue=write_queue,
        read_queue=read_queue,
        dap_resources_dir=dap_resources_dir,
    )


def dbg_wait_for(condition, msg=None, timeout=DEFAULT_TIMEOUT, sleep=1 / 20.0):
    from robocorp_ls_core.basic import wait_for_condition

    if "pydevd" in sys.modules:
        timeout = sys.maxsize

    wait_for_condition(condition, msg, timeout, sleep)
