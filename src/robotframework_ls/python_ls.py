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
import logging
import os
import sys
from robotframework_ls.robotframework_log import get_logger

try:
    import socketserver
except ImportError:
    import SocketServer as socketserver
import threading

from robotframework_ls.jsonrpc.dispatchers import MethodDispatcher
from robotframework_ls.jsonrpc.endpoint import Endpoint
from robotframework_ls.jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from . import uris
from .config import config

log = get_logger(__name__)


MAX_WORKERS = 64


class _StreamHandlerWrapper(socketserver.StreamRequestHandler, object):
    """A wrapper class that is used to construct a custom handler class."""

    delegate = None

    def setup(self):
        super(_StreamHandlerWrapper, self).setup()
        self.delegate = self.DELEGATE_CLASS(self.rfile, self.wfile)

    def handle(self):
        try:
            self.delegate.start()
        except OSError as e:
            if os.name == "nt":
                # Catch and pass on ConnectionResetError when parent process
                # dies
                if isinstance(e, WindowsError) and e.winerror == 10054:
                    pass

        self.SHUTDOWN_CALL()


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
    """ Implementation of the Microsoft VSCode Language Server Protocol
    https://github.com/Microsoft/language-server-protocol/blob/master/versions/protocol-1-x.md
    
    Based on: https://github.com/palantir/python-language-server/blob/develop/pyls/python_ls.py
    """

    def __init__(self, rx, tx, max_workers=MAX_WORKERS):
        self.workspace = None
        self.config = None
        self.root_uri = None
        self.watching_thread = None
        self.uri_workspace_mapper = {}

        self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
        self._endpoint = Endpoint(
            self, self._jsonrpc_stream_writer.write, max_workers=max_workers
        )
        self._shutdown = False

    def start(self):
        """Entry point for the server."""
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def m_shutdown(self, **_kwargs):
        self._shutdown = True
        return None

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
        **_kwargs
    ):
        from robotframework_ls._utils import exit_when_pid_exists
        from robotframework_ls.lsp import WorkspaceFolder

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
        self.config = config.Config(
            rootUri,
            initializationOptions or {},
            processId,
            _kwargs.get("capabilities", {}),
        )
        if workspaceFolders:
            workspaceFolders = [WorkspaceFolder(**w) for w in workspaceFolders]

        self.workspace = self._create_workspace(rootUri, workspaceFolders or [])

        if processId not in (None, -1, 0):
            exit_when_pid_exists(processId)

        # Get our capabilities
        return {"capabilities": self.capabilities()}

    def _create_workspace(self, root_uri, workspace_folders):
        from .workspace import Workspace

        return Workspace(root_uri, workspace_folders)

    def m_initialized(self, **_kwargs):
        pass

    def lint(self, doc_uri, is_saved):
        raise NotImplementedError("Subclasses must override.")

    def m_text_document__did_close(self, textDocument=None, **_kwargs):
        self.workspace.remove_document(textDocument["uri"])

    def m_text_document__did_open(self, textDocument=None, **_kwargs):
        from robotframework_ls.lsp import TextDocumentItem

        self.workspace.put_document(TextDocumentItem(**textDocument))
        self.lint(textDocument["uri"], is_saved=True)

    def m_text_document__did_change(
        self, contentChanges=None, textDocument=None, **_kwargs
    ):
        from robotframework_ls.lsp import TextDocumentItem
        from robotframework_ls.lsp import TextDocumentContentChangeEvent

        if contentChanges:
            for change in contentChanges:
                try:
                    self.workspace.update_document(
                        TextDocumentItem(**textDocument),
                        TextDocumentContentChangeEvent(**change),
                    )
                except:
                    log.exception(
                        "Error updating document: %s with changes: %s"
                        % (textDocument, contentChanges)
                    )
        self.lint(textDocument["uri"], is_saved=False)

    def m_text_document__did_save(self, textDocument=None, **_kwargs):
        self.lint(textDocument["uri"], is_saved=True)

    def m_workspace__did_change_configuration(self, settings=None):
        self.config.update(settings or {})

    def m_workspace__did_change_workspace_folders(self, event):
        """Adds/Removes folders from the workspace."""
        from robotframework_ls.lsp import WorkspaceFolder

        log.info("Workspace folders changed: {}".format(event))

        added_folders = event["added"] or []
        removed_folders = event["removed"] or []

        for f_add in added_folders:
            self.workspace.add_folder(WorkspaceFolder(**f_add))

        for f_remove in removed_folders:
            self.workspace.remove_folder(f_remove["uri"])

    def m_workspace__did_change_watched_files(self, changes=None, **_kwargs):
        pass


def flatten(list_of_lists):
    return [item for lst in list_of_lists for item in lst]


def merge(list_of_dicts):
    return {k: v for dictionary in list_of_dicts for k, v in dictionary.items()}
