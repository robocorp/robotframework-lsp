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
import os
import sys
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.protocols import IConfig, IWorkspace
from typing import Optional

import socketserver
import threading

from robocorp_ls_core.jsonrpc.dispatchers import MethodDispatcher
from robocorp_ls_core.jsonrpc.endpoint import Endpoint
from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from robocorp_ls_core import uris
from robocorp_ls_core.watchdog_wrapper import IFSObserver
from robocorp_ls_core.options import DEFAULT_TIMEOUT, USE_TIMEOUTS, NO_TIMEOUT

log = get_logger(__name__)


class _StreamHandlerWrapper(socketserver.StreamRequestHandler, object):
    """A wrapper class that is used to construct a custom handler class."""

    delegate = None

    def setup(self):
        super(_StreamHandlerWrapper, self).setup()
        self.delegate = self.DELEGATE_CLASS(self.rfile, self.wfile)  # noqa

    def handle(self):
        try:
            self.delegate.start()
        except OSError as e:
            if os.name == "nt":
                # Catch and pass on ConnectionResetError when parent process
                # dies
                if isinstance(e, WindowsError) and e.winerror == 10054:
                    pass

        self.SHUTDOWN_CALL()  # noqa


class _DummyStdin(object):
    def __init__(self, original_stdin=sys.stdin, *args, **kwargs):
        try:
            self.encoding = sys.stdin.encoding
        except:
            # Not sure if it's available in all Python versions...
            pass
        self.original_stdin = original_stdin

        try:
            self.errors = (
                sys.stdin.errors
            )  # Who knew? sys streams have an errors attribute!
        except:
            # Not sure if it's available in all Python versions...
            pass

    def readline(self, *args, **kwargs):
        return "\n"

    def read(self, *args, **kwargs):
        return self.readline()

    def write(self, *args, **kwargs):
        pass

    def flush(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass


def binary_stdio():
    """Construct binary stdio streams (not text mode).

    This seems to be different for Window/Unix Python2/3, so going by:
        https://stackoverflow.com/questions/2850893/reading-binary-data-from-stdin
    """
    PY3K = sys.version_info >= (3, 0)

    if PY3K:
        stdin, stdout = sys.stdin.buffer, sys.stdout.buffer
    else:
        # Python 2 on Windows opens sys.stdin in text mode, and
        # binary data that read from it becomes corrupted on \r\n
        if sys.platform == "win32":
            # set sys.stdin to binary mode
            import msvcrt

            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        stdin, stdout = sys.stdin, sys.stdout

    sys.stdin, sys.stdout = (_DummyStdin(), open(os.devnull, "w"))

    return stdin, stdout


def start_tcp_lang_client(host, port, handler_class):
    import socket as socket_module

    if not issubclass(handler_class, MethodDispatcher):
        raise ValueError("Handler class must be an instance of MethodDispatcher")

    log.info("Connecting to %s:%s", host, port)

    s = socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM)

    #  Set TCP keepalive on an open socket.
    #  It activates after 1 second (TCP_KEEPIDLE,) of idleness,
    #  then sends a keepalive ping once every 3 seconds (TCP_KEEPINTVL),
    #  and closes the connection after 5 failed ping (TCP_KEEPCNT), or 15 seconds
    try:
        s.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_KEEPALIVE, 1)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.
    try:
        s.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_KEEPIDLE, 1)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.
    try:
        s.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_KEEPINTVL, 3)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.
    try:
        s.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_KEEPCNT, 5)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.

    try:
        # 10 seconds default timeout
        s.settimeout(DEFAULT_TIMEOUT if USE_TIMEOUTS else NO_TIMEOUT)
        s.connect((host, port))
        s.settimeout(None)  # no timeout after connected
        log.info("Connected.")
    except:
        log.exception("Could not connect to %s: %s", host, port)
        raise

    log.info(
        "Starting %s IO language server. pid: %s", handler_class.__name__, os.getpid()
    )
    rfile = s.makefile("rb")
    wfile = s.makefile("wb")
    server = handler_class(rfile, wfile)
    server.start()


def start_tcp_lang_server(
    bind_addr, port, handler_class, after_bind=lambda server: None
):
    """
    :param bind_addr:
    :param port:
    :param handler_class:
    :param after_bind:
        Called right after server.bind (so, it's possible to get the port with
        server.socket.getsockname() if port 0 was passed).
    """

    def create_handler(_, *args, **kwargs):
        method_dispatcher = handler_class(*args, **kwargs)
        if not isinstance(method_dispatcher, MethodDispatcher):
            raise ValueError("Handler class must be an instance of MethodDispatcher")
        return method_dispatcher

    def shutdown_server(*args):
        log.debug("Shutting down server")
        # Shutdown call must be done on a thread, to prevent deadlocks
        stop_thread = threading.Thread(target=server.shutdown)
        stop_thread.start()

    # Construct a custom wrapper class around the user's handler_class
    wrapper_class = type(
        handler_class.__name__ + "Handler",
        (_StreamHandlerWrapper,),
        {"DELEGATE_CLASS": create_handler, "SHUTDOWN_CALL": shutdown_server},
    )

    server = socketserver.TCPServer(
        (bind_addr, port), wrapper_class, bind_and_activate=False
    )
    server.allow_reuse_address = True

    try:
        server.server_bind()
        server.server_activate()
        after_bind(server)
        log.info(
            "Serving %s on (%s, %s) - pid: %s",
            handler_class.__name__,
            bind_addr,
            port,
            os.getpid(),
        )
        server.serve_forever()
    finally:
        log.info("Shutting down")
        server.server_close()


def start_io_lang_server(rfile, wfile, handler_class):
    if not issubclass(handler_class, MethodDispatcher):
        raise ValueError("Handler class must be an instance of MethodDispatcher")
    log.info(
        "Starting %s IO language server. pid: %s", handler_class.__name__, os.getpid()
    )
    server = handler_class(rfile, wfile)
    server.start()


class PythonLanguageServer(MethodDispatcher):
    """Implementation of the Microsoft VSCode Language Server Protocol
    https://github.com/Microsoft/language-server-protocol/blob/master/versions/protocol-1-x.md

    Based on: https://github.com/palantir/python-language-server/blob/develop/pyls/python_ls.py
    """

    def __init__(self, read_stream, write_stream):
        from robocorp_ls_core.lsp import LSPMessages

        self._config: IConfig = self._create_config()
        self._workspace: Optional[IWorkspace] = None
        self.root_uri = None
        self.watching_thread = None
        self.uri_workspace_mapper = {}

        self._jsonrpc_stream_reader = JsonRpcStreamReader(read_stream)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(write_stream)
        self._endpoint = Endpoint(self, self._jsonrpc_stream_writer.write)
        self._lsp_messages = LSPMessages(self._endpoint)

        self._shutdown = False

    @property
    def workspace(self) -> Optional[IWorkspace]:
        return self._workspace

    @workspace.setter
    def workspace(self, workspace: IWorkspace) -> None:
        self._workspace = workspace
        self._config.set_workspace_dir(workspace.root_path)
        self._on_workspace_set(workspace)

    def _on_workspace_set(self, workspace: IWorkspace):
        pass

    @property  # i.e.: read-only
    def config(self) -> IConfig:
        return self._config

    def start(self):
        """Entry point for the server."""
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def m_shutdown(self, **_kwargs):
        self._shutdown = True
        workspace = self._workspace
        if workspace is not None:
            workspace.dispose()

    def m_exit(self, **_kwargs):
        self._endpoint.shutdown()
        # If there's someone reading, we could deadlock here.
        self._jsonrpc_stream_reader.close()
        self._jsonrpc_stream_writer.close()

    def capabilities(self):
        return {}  # Subclasses should override for capabilities.

    def m_initialize(
        self,
        processId=None,
        rootUri=None,
        rootPath=None,
        initializationOptions=None,
        workspaceFolders=None,
        **_kwargs,
    ) -> dict:
        from robocorp_ls_core.basic import exit_when_pid_exists
        from robocorp_ls_core.lsp import WorkspaceFolder

        log.debug(
            "Language server initialized with:\n    processId: %s\n    rootUri: %s\n    rootPath: %s\n    initializationOptions: %s\n    workspaceFolders: %s",
            processId,
            rootUri,
            rootPath,
            initializationOptions,
            workspaceFolders,
        )
        if rootUri is None:
            rootUri = uris.from_fs_path(rootPath) if rootPath is not None else ""

        self.root_uri = rootUri
        if workspaceFolders:
            workspaceFolders = [WorkspaceFolder(**w) for w in workspaceFolders]

        self.workspace = self._create_workspace(
            rootUri, self._obtain_fs_observer(), workspaceFolders or []
        )

        if processId not in (None, -1, 0):
            exit_when_pid_exists(processId)

        # Get our capabilities
        return {"capabilities": self.capabilities()}

    def _obtain_fs_observer(self) -> IFSObserver:
        """
        The FSObserver is needed to keep the list of files updated in the
        Workspace (_VirtualFS).
        """
        try:
            self._observer: IFSObserver
            return self._observer
        except AttributeError:
            from robocorp_ls_core import watchdog_wrapper

            self._observer = watchdog_wrapper.create_observer("dummy", None)
            return self._observer

    def _create_config(self) -> IConfig:
        raise NotImplementedError(f"Not implemented in: {self.__class__}")

    def _create_workspace(
        self, root_uri: str, fs_observer: IFSObserver, workspace_folders
    ) -> IWorkspace:
        from robocorp_ls_core.workspace import Workspace

        return Workspace(root_uri, fs_observer, workspace_folders)

    def m_initialized(self, **_kwargs):
        pass

    def lint(self, doc_uri, is_saved, content_changes=None):
        raise NotImplementedError(
            "Subclasses must override (current class: %s)." % (self.__class__,)
        )

    def cancel_lint(self, doc_uri):
        raise NotImplementedError(
            "Subclasses must override (current class: %s)." % (self.__class__,)
        )

    def m_text_document__did_close(self, textDocument=None, **_kwargs) -> None:
        ws = self.workspace
        doc_uri = textDocument["uri"]
        if ws is not None:
            ws.remove_document(doc_uri)
        self.cancel_lint(doc_uri)

    def m_text_document__did_open(self, textDocument=None, **_kwargs) -> None:
        from robocorp_ls_core.lsp import TextDocumentItem

        ws = self.workspace
        if ws is not None:
            ws.put_document(TextDocumentItem(**textDocument))
        self.lint(textDocument["uri"], is_saved=True, content_changes=None)

    def m_text_document__did_change(
        self, contentChanges=None, textDocument=None, **_kwargs
    ):
        from robocorp_ls_core.lsp import TextDocumentItem
        from robocorp_ls_core.lsp import TextDocumentContentChangeEvent

        if contentChanges:
            text_document_item = TextDocumentItem(**textDocument)
            for change in contentChanges:
                try:
                    range = change.get("range", None)
                    range_length = change.get("rangeLength", 0)
                    text = change.get("text", "")
                    self.workspace.update_document(
                        text_document_item,
                        TextDocumentContentChangeEvent(
                            range=range, rangeLength=range_length, text=text
                        ),
                    )
                except:
                    log.exception(
                        "Error updating document: %s with changes: %s"
                        % (textDocument, contentChanges)
                    )
        self.lint(textDocument["uri"], is_saved=False, content_changes=contentChanges)

    def m_text_document__did_save(self, textDocument=None, **_kwargs):
        self.lint(textDocument["uri"], is_saved=True, content_changes=None)

    def m_workspace__did_change_configuration(self, settings=None) -> None:
        self.config.update(settings or {})
        ws = self.workspace
        if ws:
            ws.on_changed_config(self.config)

    def m_workspace__did_change_workspace_folders(self, event=None):
        """Adds/Removes folders from the workspace."""
        from robocorp_ls_core.lsp import WorkspaceFolder

        log.info(f"Workspace folders changed: {event}")

        added_folders = []
        removed_folders = []
        if event:
            added_folders = event.get("added", [])
            removed_folders = event.get("removed", [])

        for f_add in added_folders:
            self.workspace.add_folder(WorkspaceFolder(**f_add))

        for f_remove in removed_folders:
            self.workspace.remove_folder(f_remove["uri"])

    def m_workspace__did_change_watched_files(self, changes=None, **_kwargs):
        pass

    def m_cancel_progress(self, progressId) -> bool:
        """
        Returns whether there was a match and we cancelled something from
        this process.
        """
        from robocorp_ls_core import progress_report

        if progress_report.cancel(progressId):
            log.info("Cancel progress %s", progressId)
            return True

        return False
