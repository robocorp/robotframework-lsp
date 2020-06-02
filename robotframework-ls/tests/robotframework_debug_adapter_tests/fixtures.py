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
from robocode_ls_core.unittest_tools.fixtures import TIMEOUT
import subprocess
from collections import namedtuple

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

_JsonHit = namedtuple("_JsonHit", "thread_id, frame_id, stack_trace_response")


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
    filename = str(dap_logs_dir.join("robotframework_dap_tests.log"))
    sys.stderr.write("Logging subprocess to: %s\n" % (filename,))

    yield filename


@pytest.fixture
def dap_process_stderr_file(dap_logs_dir):
    filename = str(dap_logs_dir.join("robotframework_dap_tests_stderr.log"))
    sys.stderr.write("Output subprocess stderr to: %s\n" % (filename,))
    with open(filename, "wb") as stream:
        yield stream


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
        self.target = None

    def write(self, msg):
        """
        :param BaseSchema msg:
            The message to be written.
        """
        self.write_queue.put(msg)
        return msg

    def read(self, expect_class=None, accept_msg=None):
        """
        Waits for a message and returns it (may throw error if there's a timeout waiting for the message).
        """
        from robotframework_debug_adapter.dap.dap_schema import OutputEvent

        while True:
            msg = self.read_queue.get(timeout=TIMEOUT)
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

    def initialize(self):
        from robotframework_debug_adapter.dap.dap_schema import InitializeRequest
        from robotframework_debug_adapter.dap.dap_schema import (
            InitializeRequestArguments,
        )
        from robotframework_debug_adapter.dap.dap_schema import InitializeResponse

        self.write(
            InitializeRequest(
                InitializeRequestArguments(
                    adapterID="robotframework-lsp-adapter",
                    clientID="Stub",
                    clientName="stub",
                    locale="en-us",
                    linesStartAt1=True,
                    columnsStartAt1=True,
                    pathFormat="path",
                    supportsVariableType=True,
                    supportsVariablePaging=True,
                    supportsRunInTerminalRequest=True,
                )
            )
        )

        initialize_response = self.read(InitializeResponse)
        assert isinstance(initialize_response, InitializeResponse)
        assert initialize_response.request_seq == 0
        assert initialize_response.success
        assert initialize_response.command == "initialize"

    def configuration_done(self):
        from robotframework_debug_adapter.dap.dap_schema import ConfigurationDoneRequest
        from robotframework_debug_adapter.dap.dap_schema import (
            ConfigurationDoneResponse,
        )

        self.write(ConfigurationDoneRequest())
        self.read(ConfigurationDoneResponse)

    def step_in(self, thread_id):
        from robotframework_debug_adapter.dap.dap_schema import StepInRequest
        from robotframework_debug_adapter.dap.dap_schema import StepInArguments
        from robotframework_debug_adapter.dap.dap_schema import StepInResponse

        arguments = StepInArguments(threadId=thread_id)
        self.write(StepInRequest(arguments))
        self.read(StepInResponse)

    def step_next(self, thread_id):
        from robotframework_debug_adapter.dap.dap_schema import NextRequest
        from robotframework_debug_adapter.dap.dap_schema import NextArguments
        from robotframework_debug_adapter.dap.dap_schema import NextResponse

        arguments = NextArguments(threadId=thread_id)
        self.write(NextRequest(arguments))
        self.read(NextResponse)

    def continue_event(self):
        from robotframework_debug_adapter.dap.dap_schema import ContinueRequest
        from robotframework_debug_adapter.dap.dap_schema import ContinueArguments
        from robotframework_debug_adapter.dap.dap_schema import ContinueResponse

        arguments = ContinueArguments(None)
        self.write(ContinueRequest(arguments))
        self.read(ContinueResponse)

    def launch(self, target, debug=True, success=True, terminal="none"):
        from robotframework_debug_adapter.dap.dap_schema import LaunchRequest
        from robotframework_debug_adapter.dap.dap_schema import LaunchRequestArguments
        from robotframework_debug_adapter.dap.dap_schema import LaunchResponse
        from robotframework_debug_adapter.dap.dap_schema import RunInTerminalRequest
        from robocode_ls_core.basic import as_str
        from robotframework_debug_adapter.dap.dap_schema import InitializedEvent

        self.write(
            LaunchRequest(
                LaunchRequestArguments(
                    __sessionId="some_id",
                    noDebug=not debug,
                    target=target,
                    terminal=terminal,
                )
            )
        )

        if terminal == "external":
            run_in_terminal_request = self.read(RunInTerminalRequest)
            env = os.environ.copy()
            for key, val in run_in_terminal_request.arguments.env.to_dict().items():
                env[as_str(key)] = as_str(val)
            subprocess.Popen(
                run_in_terminal_request.arguments.args,
                cwd=run_in_terminal_request.arguments.cwd,
                env=env,
            )

        if success:
            # Initialized is sent just before the launch response (at which
            # point it's possible to send breakpoints).
            event = self.read(InitializedEvent)
            assert isinstance(event, InitializedEvent)

        launch_response = self.read(LaunchResponse)
        assert launch_response.success == success

    def list_threads(self):
        from robotframework_debug_adapter.dap.dap_schema import ThreadsRequest

        return self.wait_for_response(self.write(ThreadsRequest()))

    def set_breakpoints(self, target, lines):
        import os.path
        from robotframework_debug_adapter.dap.dap_schema import SetBreakpointsRequest
        from robotframework_debug_adapter.dap.dap_schema import SetBreakpointsArguments
        from robotframework_debug_adapter.dap.dap_schema import Source
        from robotframework_debug_adapter.dap.dap_schema import SourceBreakpoint
        from robotframework_debug_adapter.dap.dap_schema import SetBreakpointsResponse

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
        from robotframework_debug_adapter.dap.dap_base_schema import get_response_class
        from robotframework_debug_adapter.dap.dap_schema import Response

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

    def get_stack_as_json_hit(self, thread_id):
        from robotframework_debug_adapter.dap.dap_schema import StackTraceArguments
        from robotframework_debug_adapter.dap.dap_schema import StackTraceRequest

        stack_trace_request = self.write(
            StackTraceRequest(StackTraceArguments(threadId=thread_id))
        )

        # : :type stack_trace_response: StackTraceResponse
        # : :type stack_trace_response_body: StackTraceResponseBody
        # : :type stack_frame: StackFrame
        stack_trace_response = self.wait_for_response(stack_trace_request)
        stack_trace_response_body = stack_trace_response.body
        assert len(stack_trace_response_body.stackFrames) > 0

        stack_frame = next(iter(stack_trace_response_body.stackFrames))

        return _JsonHit(
            thread_id=thread_id,
            frame_id=stack_frame["id"],
            stack_trace_response=stack_trace_response,
        )

    def wait_for_thread_stopped(
        self, reason="breakpoint", line=None, file=None, name=None
    ):
        """
        :param file:
            utf-8 bytes encoded file or unicode
        """
        from robotframework_debug_adapter.dap.dap_schema import StoppedEvent
        from robocode_ls_core.constants import IS_PY2

        stopped_event = self.read(StoppedEvent)
        assert stopped_event.body.reason == reason
        json_hit = self.get_stack_as_json_hit(stopped_event.body.threadId)
        if file is not None:
            path = json_hit.stack_trace_response.body.stackFrames[0]["source"]["path"]
            if IS_PY2:
                if isinstance(file, bytes):
                    file = file.decode("utf-8")
                if isinstance(path, bytes):
                    path = path.decode("utf-8")

            if not path.endswith(file):
                raise AssertionError("Expected path: %s to end with: %s" % (path, file))
        if name is not None:
            assert json_hit.stack_trace_response.body.stackFrames[0]["name"] == name
        if line is not None:
            found_line = json_hit.stack_trace_response.body.stackFrames[0]["line"]
            if not isinstance(line, (tuple, list)):
                line = [line]
            assert found_line in line, "Expect to break at line: %s. Found: %s" % (
                line,
                found_line,
            )
        return json_hit

    def get_line_index_with_content(self, line_content, filename=None):
        """
        :return the line index which has the given content (1-based).
        """
        if filename is None:
            filename = self.target
        with open(filename, "r") as stream:
            for i_line, line in enumerate(stream):
                if line_content in line:
                    return i_line + 1
        raise AssertionError("Did not find: %s in %s" % (line_content, self.TEST_FILE))

    def get_name_to_scope(self, frame_id):
        from robotframework_debug_adapter.dap.dap_schema import ScopesArguments
        from robotframework_debug_adapter.dap.dap_schema import ScopesRequest
        from robotframework_debug_adapter.dap.dap_schema import Scope

        scopes_request = self.write(ScopesRequest(ScopesArguments(frame_id)))

        scopes_response = self.wait_for_response(scopes_request)

        scopes = scopes_response.body.scopes
        name_to_scopes = dict((scope["name"], Scope(**scope)) for scope in scopes)

        assert len(scopes) == 2
        assert sorted(name_to_scopes.keys()) == ["Arguments", "Variables"]
        assert name_to_scopes["Arguments"].presentationHint == "locals"

        return name_to_scopes

    def get_name_to_var(self, variables_reference):
        from robotframework_debug_adapter.dap.dap_schema import Variable

        variables_response = self.get_variables_response(variables_reference)
        return dict(
            (variable["name"], Variable(**variable))
            for variable in variables_response.body.variables
        )

    def get_arguments_name_to_var(self, frame_id):
        name_to_scope = self.get_name_to_scope(frame_id)

        return self.get_name_to_var(name_to_scope["Arguments"].variablesReference)

    def get_variables_name_to_var(self, frame_id):
        name_to_scope = self.get_name_to_scope(frame_id)

        return self.get_name_to_var(name_to_scope["Variables"].variablesReference)

    def get_variables_response(self, variables_reference, fmt=None, success=True):
        from robotframework_debug_adapter.dap.dap_schema import VariablesRequest
        from robotframework_debug_adapter.dap.dap_schema import VariablesArguments

        variables_request = self.write(
            VariablesRequest(VariablesArguments(variables_reference, format=fmt))
        )
        variables_response = self.wait_for_response(variables_request)
        assert variables_response.success == success
        return variables_response


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
