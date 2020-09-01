from os.path import os
import json
import socket as socket_module
import sys
import threading
import traceback

try:
    import queue
except ImportError:
    import Queue as queue

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

LOG_FORMAT = "ROBOT: %(asctime)s UTC pid: %(process)d - %(threadName)s - %(levelname)s - %(name)s\n%(message)s\n\n"


def connect(port):
    from robotframework_ls.options import DEFAULT_TIMEOUT
    from robotframework_ls.impl.robot_lsp_constants import ENV_OPTION_ROBOT_DAP_TIMEOUT
    from robocorp_ls_core.robotframework_log import get_logger

    log = get_logger("robotframework_debug_adapter.run_robot__main__.py")

    #  Set TCP keepalive on an open socket.
    #  It activates after 1 second (TCP_KEEPIDLE,) of idleness,
    #  then sends a keepalive ping once every 3 seconds (TCP_KEEPINTVL),
    #  and closes the connection after 5 failed ping (TCP_KEEPCNT), or 15 seconds
    s = socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM)
    try:
        IPPROTO_TCP, SO_KEEPALIVE, TCP_KEEPIDLE, TCP_KEEPINTVL, TCP_KEEPCNT = (
            socket_module.IPPROTO_TCP,
            socket_module.SO_KEEPALIVE,
            socket_module.TCP_KEEPIDLE,  # @UndefinedVariable
            socket_module.TCP_KEEPINTVL,  # @UndefinedVariable
            socket_module.TCP_KEEPCNT,  # @UndefinedVariable
        )
        s.setsockopt(socket_module.SOL_SOCKET, SO_KEEPALIVE, 1)
        s.setsockopt(IPPROTO_TCP, TCP_KEEPIDLE, 1)
        s.setsockopt(IPPROTO_TCP, TCP_KEEPINTVL, 3)
        s.setsockopt(IPPROTO_TCP, TCP_KEEPCNT, 5)
    except AttributeError:
        pass  # May not be available everywhere.

    try:
        # 10 seconds default timeout
        timeout = int(os.environ.get(ENV_OPTION_ROBOT_DAP_TIMEOUT, DEFAULT_TIMEOUT))
        s.settimeout(timeout)
        s.connect(("127.0.0.1", port))
        s.settimeout(None)  # no timeout after connected
        log.info("Connected.")
        return s
    except:
        log.exception("Could not connect to: %s", (port,))
        raise


class _RobotTargetComm(threading.Thread):
    def __init__(self, s, debug):
        threading.Thread.__init__(self)
        self.daemon = True
        self._debug = debug
        self._socket = s
        self._write_queue = queue.Queue()
        self.configuration_done = threading.Event()
        self.terminated = threading.Event()

        log = get_log()
        if debug:
            log.debug("Patching execution context...")

            from robotframework_debug_adapter.debugger_impl import (
                install_robot_debugger,
            )

            try:
                import robot
            except ImportError:
                # If unable to import robot, don't error here (proceed as if
                # it was without debugging -- it should fail later on when
                # about to run the code, at which point the actual DAP is
                # in place).
                self._debugger_impl = None
            else:
                debugger_impl = install_robot_debugger()
                debugger_impl.busy_wait.before_wait.append(self._notify_stopped)

                log.debug("Finished patching execution context.")
                self._debugger_impl = debugger_impl
        else:
            self._debugger_impl = None

    def _notify_stopped(self):
        from robotframework_debug_adapter.dap.dap_schema import StoppedEvent
        from robotframework_debug_adapter.dap.dap_schema import StoppedEventBody
        from robotframework_debug_adapter.constants import MAIN_THREAD_ID

        reason = self._debugger_impl.stop_reason
        body = StoppedEventBody(
            reason.value, allThreadsStopped=True, threadId=MAIN_THREAD_ID
        )
        msg = StoppedEvent(body)
        self.write_message(msg)

    def start_communication_threads(self):
        from robotframework_debug_adapter.debug_adapter_threads import writer_thread
        from robotframework_debug_adapter.debug_adapter_threads import reader_thread

        read_from = self._socket.makefile("rb")
        write_to = self._socket.makefile("wb")

        writer = self._writer_thread = threading.Thread(
            target=writer_thread,
            args=(write_to, self._write_queue, "write to dap"),
            name="Write from robot to dap (_RobotTargetComm)",
        )
        writer.setDaemon(True)

        reader = self._reader_thread = threading.Thread(
            target=reader_thread,
            args=(read_from, self.process_message, self._write_queue, b"read from dap"),
            name="Read from dap to robot (_RobotTargetComm)",
        )
        reader.setDaemon(True)

        reader.start()
        writer.start()

    def terminate(self):
        from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent
        from robotframework_debug_adapter.dap.dap_schema import TerminatedEventBody

        self.write_message(TerminatedEvent(TerminatedEventBody()))

    def write_message(self, msg):
        self._write_queue.put(msg)

    def process_message(self, protocol_message):
        from robotframework_debug_adapter.constants import DEBUG
        from robotframework_debug_adapter.debug_adapter_threads import (
            READER_THREAD_STOPPED,
        )

        log = get_log()
        if protocol_message is READER_THREAD_STOPPED:
            if DEBUG:
                log.debug("%s: READER_THREAD_STOPPED." % (self.__class__.__name__,))
            return

        if DEBUG:
            log.debug(
                "Process json: %s\n"
                % (json.dumps(protocol_message.to_dict(), indent=4, sort_keys=True),)
            )

        if protocol_message.type == "request":
            method_name = "on_%s_request" % (protocol_message.command,)

        elif protocol_message.type == "event":
            method_name = "on_%s_event" % (protocol_message.event,)

        else:
            if DEBUG:
                log.debug(
                    "Unable to decide how to deal with protocol type: %s in %s.\n"
                    % (protocol_message.type, self.__class__.__name__)
                )
            return

        on_request = getattr(self, method_name, None)
        if on_request is not None:
            on_request(protocol_message)
        else:
            if DEBUG:
                log.debug(
                    "Unhandled: %s not available in %s.\n"
                    % (method_name, self.__class__.__name__)
                )

        # Note: if there's some exception, let it be processed in the caller
        # as the reader_thread does handle it properly.

    def on_terminated_event(self, event):
        self.terminated.set()

    def on_initialize_request(self, request):
        """
        :param InitializeRequest request:
        """
        from robotframework_debug_adapter.dap.dap_base_schema import build_response
        from robotframework_debug_adapter.dap.dap_schema import InitializedEvent
        from robotframework_debug_adapter.dap.dap_schema import ProcessEvent
        from robotframework_debug_adapter.dap.dap_schema import ProcessEventBody

        # : :type initialize_response: InitializeResponse
        # : :type capabilities: Capabilities
        self._initialize_request_arguments = request.arguments
        initialize_response = build_response(request)
        capabilities = initialize_response.body
        capabilities.supportsConfigurationDoneRequest = True
        self.write_message(initialize_response)
        self.write_message(
            ProcessEvent(ProcessEventBody(sys.executable, systemProcessId=os.getpid()))
        )
        self.write_message(InitializedEvent())

    def on_setBreakpoints_request(self, request):
        from robotframework_debug_adapter.dap.dap_schema import SourceBreakpoint
        from robotframework_debug_adapter.dap.dap_schema import Breakpoint
        from robotframework_debug_adapter.dap.dap_schema import (
            SetBreakpointsResponseBody,
        )
        from robotframework_debug_adapter.dap import dap_base_schema
        from robotframework_debug_adapter import file_utils
        from robotframework_debug_adapter.debugger_impl import RobotBreakpoint
        from robocorp_ls_core.robotframework_log import get_logger

        log = get_logger("robotframework_debug_adapter.run_robot__main__.py")

        # Just acknowledge that no breakpoints are valid.

        breakpoints = []
        robot_breakpoints = []
        source = request.arguments.source
        path = source.path
        filename = file_utils.norm_file_to_server(path)
        log.info("Normalized %s to %s", path, filename)

        if request.arguments.breakpoints:

            for bp in request.arguments.breakpoints:
                source_breakpoint = SourceBreakpoint(**bp)
                breakpoints.append(
                    Breakpoint(
                        verified=True, line=source_breakpoint.line, source=source
                    ).to_dict()
                )
                robot_breakpoints.append(RobotBreakpoint(source_breakpoint.line))

        if self._debugger_impl:
            self._debugger_impl.set_breakpoints(filename, robot_breakpoints)
        else:
            if robot_breakpoints:
                get_log().info("Unable to set breakpoints (no debug mode).")

        self.write_message(
            dap_base_schema.build_response(
                request,
                kwargs=dict(body=SetBreakpointsResponseBody(breakpoints=breakpoints)),
            )
        )

    def on_continue_request(self, request):
        from robotframework_debug_adapter.dap.dap_base_schema import build_response
        from robotframework_debug_adapter.dap.dap_schema import ContinueResponseBody

        response = build_response(
            request, kwargs=dict(body=ContinueResponseBody(allThreadsContinued=True))
        )

        if self._debugger_impl:
            self._debugger_impl.step_continue()
        else:
            get_log().info("Unable to continue (no debug mode).")

        self.write_message(response)

    def on_stepIn_request(self, request):
        from robotframework_debug_adapter.dap.dap_base_schema import build_response

        response = build_response(request)

        if self._debugger_impl:
            self._debugger_impl.step_in()
        else:
            get_log().info("Unable to step in (no debug mode).")
        self.write_message(response)

    def on_next_request(self, request):
        from robotframework_debug_adapter.dap.dap_base_schema import build_response

        response = build_response(request)

        if self._debugger_impl:
            self._debugger_impl.step_next()
        else:
            get_log().info("Unable to step next (no debug mode).")

        self.write_message(response)

    def on_stepOut_request(self, request):
        from robotframework_debug_adapter.dap.dap_base_schema import build_response

        response = build_response(request)

        if self._debugger_impl:
            self._debugger_impl.step_out()
        else:
            get_log().info("Unable to step out (no debug mode).")

        self.write_message(response)

    def on_threads_request(self, request):
        """
        :param ThreadsRequest request:
        """
        from robotframework_debug_adapter.dap.dap_schema import Thread
        from robotframework_debug_adapter.dap.dap_schema import ThreadsResponseBody
        from robotframework_debug_adapter.constants import MAIN_THREAD_ID
        from robotframework_debug_adapter.dap.dap_base_schema import build_response

        threads = [Thread(MAIN_THREAD_ID, "Main Thread").to_dict()]
        kwargs = {"body": ThreadsResponseBody(threads)}
        # : :type threads_response: ThreadsResponse
        threads_response = build_response(request, kwargs)
        self.write_message(threads_response)

    def on_stackTrace_request(self, request):
        """
        :param StackTraceRequest request:
        """
        from robotframework_debug_adapter.dap.dap_base_schema import build_response
        from robotframework_debug_adapter.dap.dap_schema import StackTraceResponseBody

        thread_id = request.arguments.threadId

        if self._debugger_impl:
            frames = self._debugger_impl.get_frames(thread_id)
        else:
            frames = []
            get_log().info("Unable to get stack trace (no debug mode).")

        body = StackTraceResponseBody(stackFrames=frames if frames else [])
        response = build_response(request, kwargs=dict(body=body))
        self.write_message(response)

    def on_configurationDone_request(self, request):
        """
        :param ConfigurationDoneRequest request:
        """
        from robotframework_debug_adapter.dap.dap_base_schema import build_response

        response = build_response(request)
        self.write_message(response)
        self.configuration_done.set()

    def on_scopes_request(self, request):
        """
        :param ScopesRequest request:
        """
        from robotframework_debug_adapter.dap.dap_base_schema import build_response
        from robotframework_debug_adapter.dap.dap_schema import ScopesResponseBody

        frame_id = request.arguments.frameId

        if self._debugger_impl:
            scopes = self._debugger_impl.get_scopes(frame_id)
        else:
            scopes = []
            get_log().info("Unable to step in (no debug mode).")

        body = ScopesResponseBody(scopes if scopes else [])
        response = build_response(request, kwargs=dict(body=body))
        self.write_message(response)

    def on_variables_request(self, request):
        """
        :param VariablesRequest request:
        """
        from robotframework_debug_adapter.dap.dap_base_schema import build_response
        from robotframework_debug_adapter.dap.dap_schema import VariablesResponseBody

        variables_reference = request.arguments.variablesReference

        if self._debugger_impl:
            variables = self._debugger_impl.get_variables(variables_reference)
        else:
            variables = []
            get_log().info("Unable to step in (no debug mode).")

        body = VariablesResponseBody(variables if variables else [])
        response = build_response(request, kwargs=dict(body=body))
        self.write_message(response)

    def _evaluate_response(self, request, result, error_message=""):
        from robotframework_debug_adapter.dap.dap_schema import EvaluateResponseBody
        from robotframework_debug_adapter.dap.dap_base_schema import build_response

        body = EvaluateResponseBody(result=result, variablesReference=0)
        if not error_message:
            return build_response(request, kwargs={"body": body})
        else:
            response = build_response(
                request,
                kwargs={"body": body, "success": False, "message": error_message},
            )
            return response

    def on_evaluate_request(self, request):
        frame_id = request.arguments.frameId
        expression = request.arguments.expression
        if self._debugger_impl:
            eval_info = self._debugger_impl.evaluate(frame_id, expression)
            try:
                result = eval_info.future.result()
            except Exception as e:
                err = "".join(traceback.format_exception_only(type(e), e))
                response = self._evaluate_response(request, err, error_message=err)
            else:
                response = self._evaluate_response(request, str(result))
        else:
            get_log().info("Unable to evaluate (no debug mode).")
            response = self._evaluate_response(request, "")

        self.write_message(response)


def get_log():
    from robocorp_ls_core.robotframework_log import get_logger

    return get_logger("robotframework_debug_adapter.run_robot__main__.py")


def main():
    src_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        import robotframework_ls
    except ImportError:
        # Automatically add it to the path if __main__ is being executed.
        assert os.path.exists(src_folder), "Expected: %s to exist" % (src_folder,)
        sys.path.append(src_folder)
        import robotframework_ls  # @UnusedImport
    robotframework_ls.import_robocorp_ls_core()

    from robocorp_ls_core.robotframework_log import (
        configure_logger,
        log_args_and_python,
    )

    from robotframework_debug_adapter.constants import LOG_FILENAME
    from robotframework_debug_adapter.constants import LOG_LEVEL

    configure_logger("robot", LOG_LEVEL, LOG_FILENAME)
    log = get_log()
    log_args_and_python(log, sys.argv, robotframework_ls.__version__)

    from robotframework_ls.options import DEFAULT_TIMEOUT

    args = sys.argv[1:]
    assert args[0] == "--port"
    port = args[1]
    debug = True if args[2] == "--debug" else False

    robot_args = args[3:]
    if debug:
        robot_args = [
            "--listener=robotframework_debug_adapter.listeners.DebugListener"
        ] + robot_args

    s = connect(int(port))
    processor = _RobotTargetComm(s, debug=debug)
    processor.start_communication_threads()
    if not processor.configuration_done.wait(DEFAULT_TIMEOUT):
        sys.stderr.write(
            "Process not configured for launch in the available timeout.\n"
        )
        sys.exit(1)

    try:
        try:
            import robot
        except ImportError:
            sys.stderr.write("\nError importing robot.\n")
            sys.stderr.write("Python executable: %s.\n\n" % (sys.executable,))
            raise

        from robot import run_cli

        exitcode = run_cli(robot_args, exit=False)
    finally:
        processor.terminate()
        if processor.terminated.wait(2):
            log.debug("Processed dap terminate event in robot.")
    sys.exit(exitcode)


if __name__ == "__main__":
    main()
