package robocorp.lsp.intellij.client;

import com.intellij.openapi.editor.event.EditorFactoryEvent;
import org.eclipse.lsp4j.ServerCapabilities;
import org.eclipse.lsp4j.TextDocumentSyncKind;
import org.eclipse.lsp4j.TextDocumentSyncOptions;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.junit.Assert;
import org.junit.Test;
import robocorp.lsp.intellij.*;
import robotframework.idea.RobotFrameworkLanguage;

import java.io.File;

public class LanguageServerManagerTest {

    @Test
    public void testLanguageServerManager() throws Exception {


        LanguageServerDefinition definition = RobotFrameworkLanguage.INSTANCE.getLanguageDefinition();
        // TODO: Don't hardcode this.
        String projectRoot = "X:/vscode-robot/robotframework-lsp/robotframework-idea/src/test/resources";
        File case1robot = new File(projectRoot, "case1.robot");
        String uri = Uris.toUri(case1robot);
        String extension = ".robot";

        try {
            LanguageServerManager manager = LanguageServerManager.start(definition, extension, projectRoot);
            ServerCapabilities serverCapabilities = manager.getComm(projectRoot).getServerCapabilities();
            Either<TextDocumentSyncKind, TextDocumentSyncOptions> textDocumentSync = serverCapabilities.getTextDocumentSync();
            Assert.assertEquals(TextDocumentSyncKind.Incremental, textDocumentSync.getRight().getChange());

            // Ok, manager is in place, let's open an editor and do some changes.
            LanguageServerEditorListener languageServerEditorListener = new LanguageServerEditorListener();
            languageServerEditorListener.editorCreated(EditorToLSPEditor.createStub(definition, uri, extension, projectRoot));
        } finally {
            LanguageServerManager.disposeAll();
        }

    }
}
