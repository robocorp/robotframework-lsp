package robocorp.lsp.intellij.client;

import org.eclipse.lsp4j.ServerCapabilities;
import org.eclipse.lsp4j.TextDocumentSyncKind;
import org.eclipse.lsp4j.TextDocumentSyncOptions;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.junit.Assert;
import org.junit.Test;
import robocorp.lsp.intellij.LanguageServerDefinition;
import robocorp.lsp.intellij.LanguageServerManager;
import robotframework.idea.RobotFrameworkLanguage;

public class LanguageServerManagerTest {

    @Test
    public void testLanguageServerManager() throws Exception {


        LanguageServerDefinition definition = RobotFrameworkLanguage.INSTANCE.getLanguageDefinition();
        // TODO: Don't hardcode this.
        String projectRoot = "X:\\vscode-robot\\robotframework-lsp\\robotframework-idea\\src\\test\\resources";
        try {
            LanguageServerManager manager = LanguageServerManager.start(definition, ".robot", projectRoot);
            ServerCapabilities serverCapabilities = manager.getComm(projectRoot).getServerCapabilities();
            Either<TextDocumentSyncKind, TextDocumentSyncOptions> textDocumentSync = serverCapabilities.getTextDocumentSync();
            Assert.assertEquals(TextDocumentSyncKind.Incremental, textDocumentSync.getRight().getChange());
        } finally {
            LanguageServerManager.disposeAll();
        }

    }
}
