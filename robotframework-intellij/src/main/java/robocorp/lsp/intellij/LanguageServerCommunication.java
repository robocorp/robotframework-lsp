package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.Launcher;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.eclipse.lsp4j.launch.LSPLauncher;
import org.eclipse.lsp4j.services.LanguageClient;
import org.eclipse.lsp4j.services.LanguageServer;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.management.ManagementFactory;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;

public class LanguageServerCommunication {

    public static interface IDiagnosticsListener {
        void onDiagnostics(PublishDiagnosticsParams params);
    }

    public static class DefaultLanguageClient implements LanguageClient {

        private static final Logger LOG = Logger.getInstance(DefaultLanguageClient.class);

        private final Map<String, List<IDiagnosticsListener>> uriToDiagnosticsListener = new ConcurrentHashMap<>();
        private final Object lockUriToDiagnosticsListener = new Object();

        @Override
        public void telemetryEvent(Object object) {

        }

        @Override
        public void publishDiagnostics(PublishDiagnosticsParams diagnostics) {
            String uri = diagnostics.getUri();
            List<IDiagnosticsListener> listenerList = uriToDiagnosticsListener.get(uri);
            if (listenerList != null) {
                for (IDiagnosticsListener listener : listenerList) {
                    listener.onDiagnostics(diagnostics);
                }
            }
        }

        @Override
        public void showMessage(MessageParams messageParams) {

        }

        @Override
        public CompletableFuture<MessageActionItem> showMessageRequest(ShowMessageRequestParams requestParams) {
            return null;
        }

        @Override
        public void logMessage(MessageParams message) {

        }

        public void addDiagnosticsListener(String uri, IDiagnosticsListener listener) {
            synchronized (lockUriToDiagnosticsListener) {
                List<IDiagnosticsListener> listeners = uriToDiagnosticsListener.get(uri);
                if (listeners == null) {
                    listeners = new CopyOnWriteArrayList<IDiagnosticsListener>();
                    uriToDiagnosticsListener.put(uri, listeners);
                }
                listeners.add(listener);
            }
        }

        public void removeDiagnosticsListener(String uri, IDiagnosticsListener listener) {
            synchronized (lockUriToDiagnosticsListener) {
                List<IDiagnosticsListener> listeners = uriToDiagnosticsListener.get(uri);
                if (listeners == null) {
                    listeners = new CopyOnWriteArrayList<IDiagnosticsListener>();
                    uriToDiagnosticsListener.put(uri, listeners);
                }
                listeners.remove(listener);
                if (listeners.size() == 0) {
                    uriToDiagnosticsListener.remove(uri);
                }
            }
        }
    }

    private static final Logger LOG = Logger.getInstance(LanguageServerCommunication.class);

    private final Future<Void> lifecycleFuture;
    private final LanguageServer languageServer;
    private final InitializeResult initializeResult;
    private final DefaultLanguageClient client;
    private final LanguageServerDefinition.LanguageServerStreams languageServerStreams;
    private final LanguageServerDefinition languageServerDefinition;

    public LanguageServerCommunication(String projectRootPath, LanguageServerDefinition languageServerDefinition)
            throws InterruptedException, ExecutionException, TimeoutException, IOException {

        LanguageServerDefinition.LanguageServerStreams languageServerStreams = languageServerDefinition.createConnectionProvider(projectRootPath);
        languageServerStreams.start();
        InputStream inputStream = languageServerStreams.getInputStream();
        OutputStream outputStream = languageServerStreams.getOutputStream();
        DefaultLanguageClient client = new LanguageServerCommunication.DefaultLanguageClient();
        Launcher<LanguageServer> launcher = LSPLauncher.createClientLauncher(
                client, inputStream, outputStream);

        this.languageServer = launcher.getRemoteProxy();
        this.lifecycleFuture = launcher.startListening();
        CompletableFuture<InitializeResult> initializeResultFuture = languageServer.initialize(getInitParams(projectRootPath));
        this.initializeResult = initializeResultFuture.get(10, TimeUnit.SECONDS);
        this.languageServer.initialized(new InitializedParams());
        this.client = client;
        this.languageServerStreams = languageServerStreams;
        this.languageServerDefinition = languageServerDefinition;
    }

    public void addDiagnosticsListener(String uri, IDiagnosticsListener listener) {
        this.client.addDiagnosticsListener(uri, listener);
    }

    public void removeDiagnosticsListener(String uri, IDiagnosticsListener diagnosticsListener) {
        this.client.removeDiagnosticsListener(uri, diagnosticsListener);
    }

    public void shutdown() {
        if (isConnected()) {
            try {
                lifecycleFuture.cancel(true);
                languageServer.shutdown();
                languageServer.exit();
                languageServerStreams.stop();
            } catch (Exception e) {
                LOG.error(e);
            }
        }
    }

    public boolean isConnected() {
        return lifecycleFuture != null && !lifecycleFuture.isDone() && !lifecycleFuture.isCancelled();
    }

    public boolean canSendCommands() {
        return isConnected() && initializeResult != null;
    }

    private InitializeParams getInitParams(@NotNull String projectRootPath) {
        InitializeParams initParams = new InitializeParams();
        initParams.setRootUri(Uris.pathToUri(projectRootPath));

        try {
            // Java 9 only
            initParams.setProcessId((int) ProcessHandle.current().pid());
        } catch (Exception e) {
            initParams.setProcessId(Integer.parseInt(ManagementFactory.getRuntimeMXBean().getName().split("@")[0]));
        }

        WorkspaceClientCapabilities workspaceClientCapabilities = new WorkspaceClientCapabilities();
        workspaceClientCapabilities.setApplyEdit(true);
        workspaceClientCapabilities.setDidChangeWatchedFiles(new DidChangeWatchedFilesCapabilities());
        workspaceClientCapabilities.setExecuteCommand(new ExecuteCommandCapabilities());
        workspaceClientCapabilities.setWorkspaceEdit(new WorkspaceEditCapabilities());
        workspaceClientCapabilities.setSymbol(new SymbolCapabilities());
        workspaceClientCapabilities.setWorkspaceFolders(false);
        workspaceClientCapabilities.setConfiguration(false);

        TextDocumentClientCapabilities textDocumentClientCapabilities = new TextDocumentClientCapabilities();
        textDocumentClientCapabilities.setCodeAction(new CodeActionCapabilities());
        textDocumentClientCapabilities.setCompletion(new CompletionCapabilities(new CompletionItemCapabilities(true)));
        textDocumentClientCapabilities.setDefinition(new DefinitionCapabilities());
        textDocumentClientCapabilities.setDocumentHighlight(new DocumentHighlightCapabilities());
        textDocumentClientCapabilities.setFormatting(new FormattingCapabilities());
        textDocumentClientCapabilities.setHover(new HoverCapabilities());
        textDocumentClientCapabilities.setOnTypeFormatting(new OnTypeFormattingCapabilities());
        textDocumentClientCapabilities.setRangeFormatting(new RangeFormattingCapabilities());
        textDocumentClientCapabilities.setReferences(new ReferencesCapabilities());
        textDocumentClientCapabilities.setRename(new RenameCapabilities());
        textDocumentClientCapabilities.setSemanticHighlightingCapabilities(new SemanticHighlightingCapabilities(false));
        textDocumentClientCapabilities.setSignatureHelp(new SignatureHelpCapabilities());
        textDocumentClientCapabilities.setSynchronization(new SynchronizationCapabilities(true, true, true));
        initParams.setCapabilities(
                new ClientCapabilities(workspaceClientCapabilities, textDocumentClientCapabilities, null));
        initParams.setInitializationOptions(null);

        return initParams;
    }

    public @Nullable ServerCapabilities getServerCapabilities() throws ExecutionException, InterruptedException {
        if (initializeResult != null)
            return initializeResult.getCapabilities();
        else {
            return null;
        }
    }

    public TextDocumentSyncKind getServerCapabilitySyncKind() throws ExecutionException, InterruptedException, LanguageServerUnavailableException {
        ServerCapabilities serverCapabilities = getServerCapabilities();
        if (serverCapabilities == null) {
            throw new LanguageServerUnavailableException("Server is still not initialized (capabilities unavailable).");
        }
        Either<TextDocumentSyncKind, TextDocumentSyncOptions> textDocumentSync = serverCapabilities.getTextDocumentSync();
        TextDocumentSyncKind syncKind;
        if (textDocumentSync.isLeft()) {
            syncKind = textDocumentSync.getLeft();
        } else {
            TextDocumentSyncOptions right = textDocumentSync.getRight();
            syncKind = right.getChange();
        }
        return syncKind;
    }

    public void didOpen(DidOpenTextDocumentParams params) {
        try {
            languageServer.getTextDocumentService().didOpen(params);
        } catch (Exception e) {
            LOG.error(e);
        }
    }

    public void didClose(DidCloseTextDocumentParams params) {
        try {
            languageServer.getTextDocumentService().didClose(params);
        } catch (Exception e) {
            LOG.error(e);
        }
    }

    public void didChange(DidChangeTextDocumentParams params) {
        try {
            languageServer.getTextDocumentService().didChange(params);
        } catch (Exception e) {
            LOG.error(e);
        }
    }

    public void didChangeConfiguration(DidChangeConfigurationParams params) {
        try {
            languageServer.getWorkspaceService().didChangeConfiguration(params);
        } catch (Exception e) {
            LOG.error(e);
        }
    }

    public CompletableFuture<Either<List<CompletionItem>, CompletionList>> completion(CompletionParams params) {
        return languageServer.getTextDocumentService().completion(params);
    }

    public CompletableFuture<List<? extends SymbolInformation>> symbol(WorkspaceSymbolParams symbolParams) {
        return languageServer.getWorkspaceService().symbol(symbolParams);
    }

    public CompletableFuture<Either<List<? extends Location>, List<? extends LocationLink>>> definition(DefinitionParams params) {
        return languageServer.getTextDocumentService().definition(params);
    }
}
