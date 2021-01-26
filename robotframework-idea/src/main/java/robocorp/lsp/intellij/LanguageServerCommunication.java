package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.Launcher;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.eclipse.lsp4j.services.LanguageServer;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.concurrent.*;

public class LanguageServerCommunication {

    private static final Logger LOG = Logger.getInstance(LanguageServerCommunication.class);

    private final Future<Void> future;
    private final LanguageServer languageServer;
    private final InitializeResult initializeResult;


    public LanguageServerCommunication(DefaultLanguageClient client, Launcher<LanguageServer> launcher, String projectRootPath, LanguageServerDefinition languageServerDefinition)
            throws InterruptedException, ExecutionException, TimeoutException {
        languageServer = launcher.getRemoteProxy();
        future = launcher.startListening();
        CompletableFuture<InitializeResult> initializeResultFuture = languageServer.initialize(getInitParams(projectRootPath));
        initializeResult = initializeResultFuture.get(10, TimeUnit.SECONDS);
        languageServer.initialized(new InitializedParams());
    }

    public void shutdown() {
        if (isConnected()) {
            try {
                future.cancel(true);
                languageServer.shutdown();
                languageServer.exit();
            } catch (Exception e) {
                LOG.error(e);
            }
        }
    }

    public boolean isConnected() {
        return future != null && !future.isDone() && !future.isCancelled();
    }

    public boolean canSendCommands() {
        return isConnected() && initializeResult != null;
    }

    private InitializeParams getInitParams(@NotNull String projectRootPath) {
        InitializeParams initParams = new InitializeParams();
        initParams.setRootUri(Uris.pathToUri(projectRootPath));
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
        if(serverCapabilities == null){
            throw new LanguageServerUnavailableException("Server is still not initialized (capabilities unavailable).");
        }
        Either<TextDocumentSyncKind, TextDocumentSyncOptions> textDocumentSync = serverCapabilities.getTextDocumentSync();
        TextDocumentSyncKind syncKind;
        if(textDocumentSync.isLeft()){
            syncKind = textDocumentSync.getLeft();
        }else{
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
}
