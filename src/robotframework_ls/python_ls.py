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

from pyls_jsonrpc.dispatchers import MethodDispatcher
from pyls_jsonrpc.endpoint import Endpoint
from pyls_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from . import lsp, _utils, uris
from .config import config
from .workspace import Workspace
import time

log = logging.getLogger(__name__)


PARENT_PROCESS_WATCH_INTERVAL = 3  # 3 s
MAX_WORKERS = 64
PYTHON_FILE_EXTENSIONS = (".py", ".pyi")
CONFIG_FILEs = ("pycodestyle.cfg", "setup.cfg", "tox.ini", ".flake8")


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
    if not issubclass(handler_class, PythonLanguageServer):
        raise ValueError("Handler class must be an instance of PythonLanguageServer")

    def shutdown_server(*args):
        log.debug("Shutting down server")
        # Shutdown call must be done on a thread, to prevent deadlocks
        stop_thread = threading.Thread(target=server.shutdown)
        stop_thread.start()

    # Construct a custom wrapper class around the user's handler_class
    wrapper_class = type(
        handler_class.__name__ + "Handler",
        (_StreamHandlerWrapper,),
        {"DELEGATE_CLASS": partial(handler_class,), "SHUTDOWN_CALL": shutdown_server,},
    )

    server = socketserver.TCPServer(
        (bind_addr, port), wrapper_class, bind_and_activate=False
    )
    server.allow_reuse_address = True

    try:
        server.server_bind()
        after_bind(server)
        server.server_activate()
        log.info("Serving %s on (%s, %s)", handler_class.__name__, bind_addr, port)
        server.serve_forever()
    finally:
        log.info("Shutting down")
        server.server_close()


def start_io_lang_server(rfile, wfile, handler_class):
    if not issubclass(handler_class, PythonLanguageServer):
        raise ValueError("Handler class must be an instance of PythonLanguageServer")
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
            # "completionProvider": {
            #     "resolveProvider": False,  # We know everything ahead of time
            #     "triggerCharacters": ["."],
            # },
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
                "save": {"includeText": True,},
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

        if processId not in (None, -1, 0) and self.watching_thread is None:

            def watch_parent_process(pid):
                # exit when the given pid is not alive
                while True:
                    if not _utils.is_process_alive(pid):
                        # Note: just exit since the parent process already
                        # exited.
                        log.info(
                            "Force-quit process: %s", os.getpid(),
                        )
                        os._exit(0)

                    time.sleep(PARENT_PROCESS_WATCH_INTERVAL)

            self.watching_thread = threading.Thread(
                target=watch_parent_process, args=(processId,)
            )
            self.watching_thread.daemon = True
            self.watching_thread.start()
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
        self.config.update((settings or {}).get("robot", {}))
        for workspace_uri in self.workspaces:
            workspace = self.workspaces[workspace_uri]
            workspace.update_config(self.config)
            for doc_uri in workspace.documents:
                self.lint(doc_uri, is_saved=False)

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
        changed_py_files = set()
        config_changed = False
        for d in changes or []:
            if d["uri"].endswith(PYTHON_FILE_EXTENSIONS):
                changed_py_files.add(d["uri"])
            elif d["uri"].endswith(CONFIG_FILEs):
                config_changed = True

        if config_changed:
            self.config.settings.cache_clear()
        elif not changed_py_files:
            # Only externally changed python files and lint configs may result in changed diagnostics.
            return

        for workspace_uri in self.workspaces:
            workspace = self.workspaces[workspace_uri]
            for doc_uri in workspace.documents:
                # Changes in doc_uri are already handled by m_text_document__did_save
                if doc_uri not in changed_py_files:
                    self.lint(doc_uri, is_saved=False)


def flatten(list_of_lists):
    return [item for lst in list_of_lists for item in lst]


def merge(list_of_dicts):
    return {k: v for dictionary in list_of_dicts for k, v in dictionary.items()}
