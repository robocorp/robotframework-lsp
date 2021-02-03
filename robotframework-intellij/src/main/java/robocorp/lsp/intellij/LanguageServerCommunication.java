package robocorp.lsp.intellij;

import com.intellij.openapi.application.ApplicationManager;
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
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

class InternalConnection {

    private LanguageServerDefinition.LanguageServerStreams languageServerStreams;

    private static final Logger LOG = Logger.getInstance(InternalConnection.class);

    // Passed on constructor
    private final String projectRootPath;
    private final LanguageServerDefinition languageServerDefinition;
    private final LanguageServerCommunication.DefaultLanguageClient client;

    // Set when starting
    private LanguageServer languageServer;
    private Future<Void> lifecycleFuture;
    private InitializeResult initializeResult;
    private final LanguageServerDefinition.IPreferencesListener preferencesListener;
    private final AtomicInteger counter = new AtomicInteger();

    public void shutdown() {
        languageServerDefinition.unregisterPreferencesListener(preferencesListener);
        lifecycleFuture.cancel(true);
        languageServer.shutdown();
        languageServer.exit();
        languageServerStreams.stop();
    }

    public ServerCapabilities getServerCapabilities() {
        if (initializeResult != null)
            return initializeResult.getCapabilities();
        else {
            return null;
        }
    }

    enum State {
        initialState,
        initializing,
        initialized,
        crashed
    }

    private volatile State state = State.initialState;

    private static InitializeParams getInitParams(@NotNull String projectRootPath) {
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
        textDocumentClientCapabilities.setSignatureHelp(new SignatureHelpCapabilities());
        textDocumentClientCapabilities.setSynchronization(new SynchronizationCapabilities(true, true, true));
        initParams.setCapabilities(
                new ClientCapabilities(workspaceClientCapabilities, textDocumentClientCapabilities, null));
        initParams.setInitializationOptions(null);

        return initParams;
    }

    public InternalConnection(String projectRootPath, LanguageServerDefinition languageServerDefinition, LanguageServerCommunication.DefaultLanguageClient client) {
        this.projectRootPath = projectRootPath;
        this.languageServerDefinition = languageServerDefinition;
        this.client = client;

        preferencesListener = (propName, oldValue, newValue) -> {
            // Whenever preferences change, send it to the server.
            if (!isConnected()) {
                return;
            }
            final int currValue = counter.incrementAndGet();
            ApplicationManager.getApplication().invokeLater(() -> {
                if (counter.get() == currValue) {
                    // i.e.: if we receive multiple notifications at once, notify only once in the last notification.
                    this.didChangeConfiguration(new DidChangeConfigurationParams(languageServerDefinition.getPreferences()));
                }
            });
        };
    }

    public void start() {
        if (state != State.initialState) {
            // Can only initialize when on the initial state.
            return;
        }
        try {
            state = State.initializing;
            LanguageServerDefinition.LanguageServerStreams languageServerStreams = languageServerDefinition.createConnectionProvider(projectRootPath);
            languageServerStreams.start();
            InputStream inputStream = languageServerStreams.getInputStream();
            OutputStream outputStream = languageServerStreams.getOutputStream();
            Launcher<LanguageServer> launcher = LSPLauncher.createClientLauncher(
                    client, inputStream, outputStream);

            this.languageServer = launcher.getRemoteProxy();
            this.lifecycleFuture = launcher.startListening();
            CompletableFuture<InitializeResult> initializeResultFuture = languageServer.initialize(getInitParams(projectRootPath));
            InitializeResult tempResult = null;
            for (int i = 0; i < 10; i++) {
                try {
                    tempResult = initializeResultFuture.get(1, TimeUnit.SECONDS);
                } catch (InterruptedException | ExecutionException | TimeoutException e) {
                    if (!this.isConnected() || i == 9) {
                        throw e;
                    }
                }
            }
            initializeResult = tempResult;
            this.languageServerStreams = languageServerStreams;

            this.didChangeConfiguration(new DidChangeConfigurationParams(languageServerDefinition.getPreferences()));
            languageServerDefinition.registerPreferencesListener(preferencesListener);
            this.languageServer.initialized(new InitializedParams());

        } catch (Exception e) {
            LOG.error(e);
            state = State.crashed;
        }
    }

    boolean isConnected() {
        return lifecycleFuture != null && !lifecycleFuture.isDone() && !lifecycleFuture.isCancelled();
    }

    public void didChangeConfiguration(DidChangeConfigurationParams params) {
        if (!this.isConnected()) {
            LOG.info("Unable to change config: disconnected.");
            return;
        }
        try {
            languageServer.getWorkspaceService().didChangeConfiguration(params);
        } catch (Exception e) {
            LOG.error(e);
        }
    }

    /*default*/ LanguageServer getLanguageServer() {
        return languageServer;
    }
}

public class LanguageServerCommunication {

    public interface IDiagnosticsListener {
        void onDiagnostics(PublishDiagnosticsParams params);
    }

    public static class DefaultLanguageClient implements LanguageClient {

        private static final Logger LOG = Logger.getInstance(DefaultLanguageClient.class);

        private final Map<String, Collection<IDiagnosticsListener>> uriToDiagnosticsListener = new ConcurrentHashMap<>();
        private final Object lockUriToDiagnosticsListener = new Object();

        @Override
        public void telemetryEvent(Object object) {

        }

        @Override
        public void publishDiagnostics(PublishDiagnosticsParams diagnostics) {
            String uri = diagnostics.getUri();
            Collection<IDiagnosticsListener> listenerList = uriToDiagnosticsListener.get(uri);
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
                Collection<IDiagnosticsListener> listeners = uriToDiagnosticsListener.get(uri);
                if (listeners == null) {
                    listeners = new CopyOnWriteArraySet<>();
                    uriToDiagnosticsListener.put(uri, listeners);
                }
                listeners.add(listener);
            }
        }

        public void removeDiagnosticsListener(String uri, IDiagnosticsListener listener) {
            synchronized (lockUriToDiagnosticsListener) {
                Collection<IDiagnosticsListener> listeners = uriToDiagnosticsListener.get(uri);
                if (listeners == null) {
                    listeners = new CopyOnWriteArraySet<>();
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

    private final DefaultLanguageClient client;
    private final LanguageServerDefinition languageServerDefinition;
    private InternalConnection internalConnection;

    // i.e.: after disposed the communication won't be restored!
    private volatile boolean disposed = false;

    public LanguageServerCommunication(String projectRootPath, LanguageServerDefinition languageServerDefinition)
            throws InterruptedException, ExecutionException, TimeoutException, IOException {
        DefaultLanguageClient client = new DefaultLanguageClient();
        this.internalConnection = new InternalConnection(projectRootPath, languageServerDefinition, client);
        internalConnection.start();

        this.client = client;
        this.languageServerDefinition = languageServerDefinition;
    }

    public void addDiagnosticsListener(String uri, IDiagnosticsListener listener) {
        this.client.addDiagnosticsListener(uri, listener);
    }

    public void removeDiagnosticsListener(String uri, IDiagnosticsListener diagnosticsListener) {
        this.client.removeDiagnosticsListener(uri, diagnosticsListener);
    }

    public void shutdown(boolean dispose) {
        if (dispose) {
            // When disposed it won't be restarted anymore.
            this.disposed = true;
        }
        if (internalConnection.isConnected()) {
            try {
                internalConnection.shutdown();
            } catch (Exception e) {
                LOG.error(e);
            }
        }
    }

    public @Nullable ServerCapabilities getServerCapabilities() throws ExecutionException, InterruptedException {
        return internalConnection.getServerCapabilities();
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

    private LanguageServer obtainSynchronizedLanguageServer() {
        if (!internalConnection.isConnected()) {
            // XXX: We must restart if it's not connected (and when restarted the docs/settings
            // must be set again).
            return null;
        }
        LanguageServer languageServer = internalConnection.getLanguageServer();
        return languageServer;
    }

    public void didOpen(EditorLanguageServerConnection editorLanguageServerConnection) {
        DidOpenTextDocumentParams params = editorLanguageServerConnection.getDidOpenTextDocumentParams();
        if (params == null) {
            return;
        }
        this.didOpen(params);
    }

    private void didOpen(DidOpenTextDocumentParams params) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable forward open: disconnected.");
            return;
        }
        try {
            languageServer.getTextDocumentService().didOpen(params);
        } catch (Exception e) {
            LOG.error(e);
        }
    }

    public void didClose(EditorLanguageServerConnection editorLanguageServerConnection) {
        this.didClose(new DidCloseTextDocumentParams(editorLanguageServerConnection.getIdentifier()));
    }

    private void didClose(DidCloseTextDocumentParams params) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable forward close: disconnected.");
            return;
        }
        try {
            languageServer.getTextDocumentService().didClose(params);
        } catch (Exception e) {
            LOG.error(e);
        }
    }

    public void didChange(DidChangeTextDocumentParams params) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable forward change: disconnected.");
            return;
        }
        try {
            languageServer.getTextDocumentService().didChange(params);
        } catch (Exception e) {
            LOG.error(e);
        }
    }

    public @Nullable CompletableFuture<Either<List<CompletionItem>, CompletionList>> completion(CompletionParams params) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable to get symbol: disconnected.");
            return null;
        }
        return languageServer.getTextDocumentService().completion(params);
    }

    public @Nullable CompletableFuture<List<? extends SymbolInformation>> symbol(WorkspaceSymbolParams symbolParams) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable to get symbol: disconnected.");
            return null;
        }
        return languageServer.getWorkspaceService().symbol(symbolParams);
    }

    public @Nullable CompletableFuture<Either<List<? extends Location>, List<? extends LocationLink>>> definition(DefinitionParams params) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable to get definition: disconnected.");
            return null;
        }

        return languageServer.getTextDocumentService().definition(params);
    }

    public @Nullable CompletableFuture<Object> command(ExecuteCommandParams params) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable to run command: disconnected.");
            return null;
        }

        return languageServer.getWorkspaceService().executeCommand(params);
    }
}
