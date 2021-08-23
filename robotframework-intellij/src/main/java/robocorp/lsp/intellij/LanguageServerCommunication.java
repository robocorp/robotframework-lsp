package robocorp.lsp.intellij;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.project.Project;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.Launcher;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.eclipse.lsp4j.launch.LSPLauncher;
import org.eclipse.lsp4j.services.LanguageClient;
import org.eclipse.lsp4j.services.LanguageServer;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.InputStream;
import java.io.OutputStream;
import java.lang.management.ManagementFactory;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

class InternalConnection {

    private LanguageServerDefinition.LanguageServerStreams languageServerStreams;

    private static final Logger LOG = Logger.getInstance(InternalConnection.class);

    // Passed on constructor
    private final Project project;
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
        try {
            languageServerDefinition.unregisterPreferencesListener(project, preferencesListener);
            if (isConnected()) {
                lifecycleFuture.cancel(true);
                try {
                    languageServer.shutdown().get(1, TimeUnit.SECONDS);
                } catch (Exception e) {
                    // ignore
                }
                languageServer.exit();
                languageServerStreams.stop();
            }

        } catch (ProcessCanceledException | CompletionException | CancellationException e) {
            // ignore
        } catch (Exception e) {
            LOG.error(e);
        } finally {
            state = State.finished;
        }
    }

    public ServerCapabilities getServerCapabilities() {
        if (initializeResult != null)
            return initializeResult.getCapabilities();
        else {
            return null;
        }
    }

    enum State {
        initial, // Just created
        initializing, // Initializing started
        initialized, // Properly initialized (ok to use)
        finished, // shutdown
        crashed; // crashed while initializing
    }

    private volatile State state = State.initial;

    public State getState() {
        return state;
    }

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

    public InternalConnection(Project project, String projectRootPath, LanguageServerDefinition languageServerDefinition, LanguageServerCommunication.DefaultLanguageClient client) {
        this.projectRootPath = projectRootPath;
        this.languageServerDefinition = languageServerDefinition;
        this.client = client;
        this.project = project;

        preferencesListener = (propName, oldValue, newValue) -> {
            // Whenever preferences change, send it to the server.
            if (!isConnected()) {
                return;
            }
            final int currValue = counter.incrementAndGet();
            ApplicationManager.getApplication().invokeLater(() -> {
                if (counter.get() == currValue) {
                    // i.e.: if we receive multiple notifications at once, notify only once in the last notification.
                    this.didChangeConfiguration(new DidChangeConfigurationParams(languageServerDefinition.getPreferences(project)));
                }
            });
        };
    }

    public boolean isProperlyConfigured() {
        return languageServerDefinition.createConnectionProvider() != null;
    }

    public void start(Set<EditorLanguageServerConnection> editorConnections) {
        if (state != State.initial) {
            // Can only initialize when on the initial state.
            return;
        }
        try {
            state = State.initializing;
            LanguageServerDefinition.LanguageServerStreams languageServerStreams = languageServerDefinition.createConnectionProvider();
            if (languageServerStreams == null) {
                // Configuration is not valid. Bail out.
                LOG.info("languageServerDefinition.createConnectionProvider() returned null, marking as crashed.");
                state = State.crashed;
                return;
            }
            languageServerStreams.start();
            InputStream inputStream = languageServerStreams.getInputStream();
            OutputStream outputStream = languageServerStreams.getOutputStream();
            LOG.info("Setting up language server communication.");
            Launcher<LanguageServer> launcher = LSPLauncher.createClientLauncher(
                    client, inputStream, outputStream);

            this.languageServer = launcher.getRemoteProxy();
            this.lifecycleFuture = launcher.startListening();
            LOG.info("Sending initialize message to language server.");
            CompletableFuture<InitializeResult> initializeResultFuture = languageServer.initialize(getInitParams(projectRootPath));
            InitializeResult tempResult = null;
            int timeoutInSeconds = 15;
            for (int i = 0; i < timeoutInSeconds; i++) {
                try {
                    tempResult = initializeResultFuture.get(1, TimeUnit.SECONDS);
                    break;
                } catch (InterruptedException | ExecutionException | TimeoutException e) {
                    languageServerStreams.verifyProcess();
                    if (!this.isConnected() || i == timeoutInSeconds - 1) {
                        LOG.info("Initialize was not received from the language server in the expected timeout.");
                        throw e;
                    }
                }
            }
            LOG.info("Initialize properly received from the language server.");
            initializeResult = tempResult;
            this.languageServerStreams = languageServerStreams;

            this.didChangeConfiguration(new DidChangeConfigurationParams(languageServerDefinition.getPreferences(project)));
            languageServerDefinition.registerPreferencesListener(project, preferencesListener);

            for (EditorLanguageServerConnection editorLanguageServerConnection : editorConnections) {
                try {
                    languageServer.getTextDocumentService().didOpen(editorLanguageServerConnection.getDidOpenTextDocumentParams());
                } catch (Exception e) {
                    EditorUtils.logError(LOG, e);
                }
            }

            this.languageServer.initialized(new InitializedParams());
            state = State.initialized;

        } catch (Exception e) {
            LOG.info("Exception while initializing. Marking as crashed.");
            EditorUtils.logError(LOG, e);
            state = State.crashed;
        }
    }

    boolean isConnected() {
        return state == State.initialized && lifecycleFuture != null && !lifecycleFuture.isDone() && !lifecycleFuture.isCancelled();
    }

    public void didChangeConfiguration(DidChangeConfigurationParams params) {
        if (state != State.initializing && !this.isConnected()) {
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

    private final String projectRootPath;
    private final Project project;

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
    private final Object internalConnectionLock = new Object();
    private final Object disposeLock = new Object();

    private InternalConnection internalConnection;

    private final Callbacks.ICallback<LanguageServerDefinition> onChangedLanguageDefinition = (obj) -> {
        // i.e.: enable it to be restarted.
        crashCount = 0;

        // It should auto-restart when needed.
        shutdown(false);
    };

    // i.e.: after disposed the communication won't be restored!
    private volatile boolean disposed = false;
    private volatile int crashCount = 0;

    public int getCrashCount() {
        return crashCount;
    }

    // When reinitializing we must send open events for the existing editors.
    // Note that it's not thread safe and access must sync on `internalConnectionLock` as it's
    // used during initialization.
    private final Set<EditorLanguageServerConnection> editorConnections = new HashSet<>();

    public LanguageServerCommunication(Project project, String projectRootPath, LanguageServerDefinition languageServerDefinition) {
        DefaultLanguageClient client = new DefaultLanguageClient();
        this.projectRootPath = projectRootPath;
        this.project = project;
        this.client = client;
        this.languageServerDefinition = languageServerDefinition;

        languageServerDefinition.onChangedLanguageDefinition.register(onChangedLanguageDefinition);

        this.startInternalConnection();
    }

    private void startInternalConnection() {
        synchronized (internalConnectionLock) {
            while (true) {
                if (crashCount >= 5) {
                    EditorUtils.logError(LOG, "The language server already crashed 5 times when starting, so, it won't be restarted again until a configuration change or restart.");
                    return;
                }
                if (this.internalConnection != null) {
                    this.internalConnection.shutdown();
                }
                this.internalConnection = new InternalConnection(project, projectRootPath, languageServerDefinition, client);
                internalConnection.start(editorConnections);
                InternalConnection.State state = internalConnection.getState();
                if (state == InternalConnection.State.initialized) {
                    crashCount = 0; // When a successful initialization is done, reset the crash count.
                    return;
                } else {
                    crashCount += 1;
                    EditorUtils.logError(LOG, "Expected state to be initialized. Current state is: " + state);
                }
            }
        }
    }

    private @Nullable LanguageServer obtainSynchronizedLanguageServer() {
        if (disposed) {
            return null;
        }
        synchronized (internalConnectionLock) {
            if (!internalConnection.isConnected()) {
                if (!internalConnection.isProperlyConfigured()) {
                    return null;
                }
                startInternalConnection();
                if (!internalConnection.isConnected()) {
                    return null;
                }
            }
            LanguageServer languageServer = internalConnection.getLanguageServer();
            return languageServer;
        }
    }

    public void shutdown(boolean dispose) {
        synchronized (disposeLock) {
            if (this.disposed) {
                return;
            }
            if (dispose) {
                // When disposed it won't be restarted anymore.
                this.disposed = true;
            }
        }
        try {
            internalConnection.shutdown();
        } catch (Exception e) {
            LOG.error(e);
        }
    }

    public void addDiagnosticsListener(String uri, IDiagnosticsListener listener) {
        this.client.addDiagnosticsListener(uri, listener);
    }

    public void removeDiagnosticsListener(String uri, IDiagnosticsListener diagnosticsListener) {
        this.client.removeDiagnosticsListener(uri, diagnosticsListener);
    }

    public @Nullable ServerCapabilities getServerCapabilities() {
        return internalConnection.getServerCapabilities();
    }

    public TextDocumentSyncKind getServerCapabilitySyncKind() throws LanguageServerUnavailableException {
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

    public void didOpen(EditorLanguageServerConnection editorLanguageServerConnection) {
        DidOpenTextDocumentParams params = editorLanguageServerConnection.getDidOpenTextDocumentParams();
        if (params == null) {
            return;
        }
        LanguageServer languageServer = obtainSynchronizedLanguageServer();
        synchronized (internalConnectionLock) {
            // ObtainSynchronizedLanguageServer may create a new language server,
            // so, we only want to add the connections after that so that there's
            // no double `didOpen` message.
            editorConnections.add(editorLanguageServerConnection);
        }

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
        synchronized (internalConnectionLock) {
            editorConnections.remove(editorLanguageServerConnection);
        }
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable forward close: disconnected.");
            return;
        }
        try {
            languageServer.getTextDocumentService().didClose(new DidCloseTextDocumentParams(editorLanguageServerConnection.getIdentifier()));
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
        languageServer.getTextDocumentService().didChange(params);
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
            LOG.info("Unable to get workspace symbol: disconnected.");
            return null;
        }
        return languageServer.getWorkspaceService().symbol(symbolParams);
    }

    public CompletableFuture<List<Either<SymbolInformation, DocumentSymbol>>> documentSymbol(DocumentSymbolParams documentSymbolParams) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable to get document symbol: disconnected.");
            return null;
        }
        return languageServer.getTextDocumentService().documentSymbol(documentSymbolParams);
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

    public CompletableFuture<SemanticTokens> getSemanticTokens(SemanticTokensParams params) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable to run command: disconnected.");
            return null;
        }

        return languageServer.getTextDocumentService().semanticTokensFull(params);
    }

    public @Nullable CompletableFuture<Hover> hover(HoverParams params) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable to get hover: disconnected.");
            return null;
        }
        return languageServer.getTextDocumentService().hover(params);
    }

    public CompletableFuture<List<FoldingRange>> getFoldingRanges(FoldingRangeRequestParams params) {
        LanguageServer languageServer = obtainSynchronizedLanguageServer();

        if (languageServer == null) {
            LOG.info("Unable to run command: disconnected.");
            return null;
        }

        return languageServer.getTextDocumentService().foldingRange(params);

    }

}
