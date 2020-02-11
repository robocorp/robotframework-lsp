# Copyright 2017 Palantir Technologies, Inc.
# License: MIT
from functools import partial
import logging
import os

try:
    import socketserver
except ImportError:
    import SocketServer as socketserver
import threading

from robotframework_ls.jsonrpc.dispatchers import MethodDispatcher
from robotframework_ls.jsonrpc.endpoint import Endpoint
from robotframework_ls.jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from . import lsp, _utils, uris
from .config import config
from .workspace import Workspace

log = logging.getLogger(__name__)


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


class RedirectedStreamErrorOnAccess(object):
    def __getattr__(self, mname):
        raise AssertionError("This stream is now redirected and should not be used.")


def binary_stdio():
    """Construct binary stdio streams (not text mode).

    This seems to be different for Window/Unix Python2/3, so going by:
        https://stackoverflow.com/questions/2850893/reading-binary-data-from-stdin
    """
    import sys

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

    sys.stdin, sys.stdout = (
        RedirectedStreamErrorOnAccess(),
        RedirectedStreamErrorOnAccess(),
    )

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
    if not issubclass(handler_class, MethodDispatcher):
        raise ValueError("Handler class must be an instance of MethodDispatcher")

    def shutdown_server(*args):
        log.debug("Shutting down server")
        # Shutdown call must be done on a thread, to prevent deadlocks
        stop_thread = threading.Thread(target=server.shutdown)
        stop_thread.start()

    # Construct a custom wrapper class around the user's handler_class
    wrapper_class = type(
        handler_class.__name__ + "Handler",
        (_StreamHandlerWrapper,),
        {"DELEGATE_CLASS": partial(handler_class), "SHUTDOWN_CALL": shutdown_server},
    )

    server = socketserver.TCPServer(
        (bind_addr, port), wrapper_class, bind_and_activate=False
    )
    server.allow_reuse_address = True

    try:
        server.server_bind()
        server.server_activate()
        after_bind(server)
        log.info("Serving %s on (%s, %s)", handler_class.__name__, bind_addr, port)
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

    def __init__(self, rx, tx):
        self.workspace = None
        self.config = None
        self.root_uri = None
        self.watching_thread = None
        self.workspaces = {}
        self.uri_workspace_mapper = {}

        self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
        self._endpoint = Endpoint(
            self, self._jsonrpc_stream_writer.write, max_workers=MAX_WORKERS
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
        self._jsonrpc_stream_reader.close()
        self._jsonrpc_stream_writer.close()

    def _match_uri_to_workspace(self, uri):
        workspace_uri = _utils.match_uri_to_workspace(uri, self.workspaces)
        return self.workspaces.get(workspace_uri, self.workspace)

    def capabilities(self):
        server_capabilities = {
            "codeActionProvider": False,
            # "codeLensProvider": {
            #     "resolveProvider": False,  # We may need to make this configurable
            # },
            "completionProvider": {
                "resolveProvider": False  # We know everything ahead of time
            },
            "documentFormattingProvider": False,
            "documentHighlightProvider": False,
            "documentRangeFormattingProvider": False,
            "documentSymbolProvider": False,
            "definitionProvider": False,
            "executeCommandProvider": {"commands": []},
            "hoverProvider": False,
            "referencesProvider": False,
            "renameProvider": False,
            "foldingRangeProvider": False,
            # "signatureHelpProvider": {
            #     'triggerCharacters': ['(', ',', '=']
            # },
            "textDocumentSync": {
                "change": lsp.TextDocumentSyncKind.INCREMENTAL,
                "save": {"includeText": True},
                "openClose": True,
            },
            "workspace": {
                "workspaceFolders": {"supported": True, "changeNotifications": True}
            },
        }
        log.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

    def m_initialize(
        self,
        processId=None,
        rootUri=None,
        rootPath=None,
        initializationOptions=None,
        **_kwargs
    ):
        from robotframework_ls._utils import exit_when_pid_exists

        log.debug(
            "Language server initialized with:\n    processId: %s\n    rootUri: %s\n    rootPath: %s\n    initializationOptions: %s",
            processId,
            rootUri,
            rootPath,
            initializationOptions,
        )
        if rootUri is None:
            rootUri = uris.from_fs_path(rootPath) if rootPath is not None else ""

        self.workspaces.pop(self.root_uri, None)
        self.root_uri = rootUri
        self.config = config.Config(
            rootUri,
            initializationOptions or {},
            processId,
            _kwargs.get("capabilities", {}),
        )
        self.workspace = Workspace(rootUri, self._endpoint, self.config)
        self.workspaces[rootUri] = self.workspace

        if processId not in (None, -1, 0):
            exit_when_pid_exists(processId)

        # Get our capabilities
        return {"capabilities": self.capabilities()}

    def m_initialized(self, **_kwargs):
        pass

    def lint(self, doc_uri, is_saved):
        raise NotImplementedError("Subclasses must override.")

    def m_text_document__did_close(self, textDocument=None, **_kwargs):
        workspace = self._match_uri_to_workspace(textDocument["uri"])
        workspace.rm_document(textDocument["uri"])

    def m_text_document__did_open(self, textDocument=None, **_kwargs):
        workspace = self._match_uri_to_workspace(textDocument["uri"])
        if workspace is None:
            log.critical("Unable to find workspace for: %s", (textDocument,))
            return
        workspace.put_document(
            textDocument["uri"],
            textDocument["text"],
            version=textDocument.get("version"),
        )
        self.lint(textDocument["uri"], is_saved=True)

    def m_text_document__did_change(
        self, contentChanges=None, textDocument=None, **_kwargs
    ):
        workspace = self._match_uri_to_workspace(textDocument["uri"])
        if workspace is None:
            log.critical("Unable to find workspace for: %s", (textDocument,))
            return

        for change in contentChanges:
            workspace.update_document(
                textDocument["uri"], change, version=textDocument.get("version")
            )
        self.lint(textDocument["uri"], is_saved=False)

    def m_text_document__did_save(self, textDocument=None, **_kwargs):
        self.lint(textDocument["uri"], is_saved=True)

    def m_workspace__did_change_configuration(self, settings=None):
        self.config.update(settings or {})

    def m_workspace__did_change_workspace_folders(
        self, added=None, removed=None, **_kwargs
    ):
        for removed_info in removed:
            removed_uri = removed_info["uri"]
            self.workspaces.pop(removed_uri)

        for added_info in added:
            added_uri = added_info["uri"]
            self.workspaces[added_uri] = Workspace(
                added_uri, self._endpoint, self.config
            )

        # Migrate documents that are on the root workspace and have a better
        # match now
        doc_uris = list(self.workspace._docs.keys())
        for uri in doc_uris:
            doc = self.workspace._docs.pop(uri)
            new_workspace = self._match_uri_to_workspace(uri)
            new_workspace._docs[uri] = doc

    def m_workspace__did_change_watched_files(self, changes=None, **_kwargs):
        pass


def flatten(list_of_lists):
    return [item for lst in list_of_lists for item in lst]


def merge(list_of_dicts):
    return {k: v for dictionary in list_of_dicts for k, v in dictionary.items()}
