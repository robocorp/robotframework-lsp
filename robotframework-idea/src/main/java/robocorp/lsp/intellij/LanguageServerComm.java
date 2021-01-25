package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.Launcher;
import org.eclipse.lsp4j.services.LanguageServer;
import org.jetbrains.annotations.NotNull;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;

public class LanguageServerComm {

    private final Future<Void> future;
    private final LanguageServer languageServer;
    private static final Logger LOG = Logger.getInstance(LanguageServerComm.class);
    private final CompletableFuture<InitializeResult> initializeResult;

    public LanguageServerComm(DefaultLanguageClient client, Launcher<LanguageServer> launcher, String projectRootPath, LanguageServerDefinition languageServerDefinition) {
        languageServer = launcher.getRemoteProxy();
        future = launcher.startListening();
        initializeResult = languageServer.initialize(getInitParams(projectRootPath));
        while (!initializeResult.isDone()){
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                LOG.error(e);
            }
        }
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
        return isConnected() && initializeResult.isDone();
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

    public ServerCapabilities getServerCapabilities() throws ExecutionException, InterruptedException {
        if (initializeResult != null)
            return initializeResult.get().getCapabilities();
        else {
            return null;
        }
    }
}
