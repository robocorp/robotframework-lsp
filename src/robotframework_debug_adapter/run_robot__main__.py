import sys
import socket as socket_module
from os.path import os
import threading
import json

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
    from robotframework_ls.robotframework_log import get_logger

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


class _DAPCommandProcessor(threading.Thread):
    def __init__(self, s):
        threading.Thread.__init__(self)
        self.daemon = True
        self._socket = s
        self._write_queue = queue.Queue()
        self.configuration_done = threading.Event()
        self.terminated = threading.Event()

    def start_communication_threads(self):
        from robotframework_debug_adapter.debug_adapter_threads import writer_thread
        from robotframework_debug_adapter.debug_adapter_threads import reader_thread

        read_from = self._socket.makefile("rb")
        write_to = self._socket.makefile("wb")

        writer = self._writer_thread = threading.Thread(
            target=writer_thread, args=(write_to, self._write_queue, "write to dap")
        )
        writer.setDaemon(True)

        reader = self._reader_thread = threading.Thread(
            target=reader_thread,
            args=(read_from, self.process_message, self._write_queue, b"read from dap"),
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
        from robotframework_ls.robotframework_log import get_logger
        from robotframework_debug_adapter.constants import DEBUG
        from robotframework_debug_adapter.debug_adapter_threads import (
            READER_THREAD_STOPPED,
        )

        log = get_logger("robotframework_debug_adapter.run_robot__main__.py")
        if protocol_message is READER_THREAD_STOPPED:
            if DEBUG:
                log.debug("_DAPCommandProcessor: READER_THREAD_STOPPED.")
            return

        if DEBUG:
            log.debug(
                "Process json: %s\n"
                % (json.dumps(protocol_message.to_dict(), indent=4, sort_keys=True),)
            )

        try:
            if protocol_message.type == "request":
                method_name = "on_%s_request" % (protocol_message.command,)

            elif protocol_message.type == "event":
                method_name = "on_%s_event" % (protocol_message.event,)

            else:
                if DEBUG:
                    log.debug(
                        "Unable to decide how to deal with protocol type: %s in _DAPCommandProcessor.\n"
                        % (protocol_message.type,)
                    )
                return

            on_request = getattr(self, method_name, None)
            if on_request is not None:
                on_request(protocol_message)
            else:
                if DEBUG:
                    log.debug(
                        "Unhandled: %s not available in CommandProcessor.\n"
                        % (method_name,)
                    )
        except:
            log.exception("Error")

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

    def on_configurationDone_request(self, request):
        """
        :param ConfigurationDoneRequest request:
        """
        from robotframework_debug_adapter.dap.dap_base_schema import build_response

        response = build_response(request)
        self.write_message(response)
        self.configuration_done.set()


def main():
    try:
        import robotframework_ls
    except ImportError:
        # Automatically add it to the path if __main__ is being executed.
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import robotframework_ls  # @UnusedImport

    from robotframework_ls.robotframework_log import (
        configure_logger,
        log_args_and_python,
    )
    from robotframework_ls.robotframework_log import get_logger

    configure_logger("robot")
    log = get_logger("robotframework_debug_adapter.run_robot__main__.py")
    log_args_and_python(log, sys.argv)

    from robotframework_ls.options import DEFAULT_TIMEOUT

    args = sys.argv[1:]
    assert args[0] == "--port"
    port = args[1]

    robot_args = args[2:]

    s = connect(int(port))
    processor = _DAPCommandProcessor(s)
    processor.start_communication_threads()
    if not processor.configuration_done.wait(DEFAULT_TIMEOUT):
        sys.stderr.write(
            "Process not configured for launch in the available timeout.\n"
        )
        sys.exit(1)

    try:
        from robot import run_cli

        exitcode = run_cli(robot_args, exit=False)
    finally:
        processor.terminate()
        if processor.terminated.wait(2):
            log.debug("Processed dap terminate event in robot.")
    sys.exit(exitcode)


if __name__ == "__main__":
    main()
