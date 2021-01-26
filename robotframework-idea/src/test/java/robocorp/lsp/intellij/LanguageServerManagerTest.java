package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.testFramework.fixtures.BasePlatformTestCase;
import org.eclipse.lsp4j.ServerCapabilities;
import org.eclipse.lsp4j.TextDocumentSyncKind;
import org.eclipse.lsp4j.TextDocumentSyncOptions;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.junit.Assert;
import org.junit.Test;
import robotframework.idea.RobotFrameworkLanguage;

import java.io.File;

public class LanguageServerManagerTest extends BasePlatformTestCase {
    private static final Logger LOG = Logger.getInstance(LanguageServerManagerTest.class);

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
            ServerCapabilities serverCapabilities = manager.getLanguageServerCommunication(extension, projectRoot).getServerCapabilities();
            Either<TextDocumentSyncKind, TextDocumentSyncOptions> textDocumentSync = serverCapabilities.getTextDocumentSync();
            Assert.assertEquals(TextDocumentSyncKind.Incremental, textDocumentSync.getRight().getChange());

            // Ok, manager is in place, let's open an editor and do some changes.
            LanguageServerEditorListener languageServerEditorListener = new LanguageServerEditorListener();
            EditorToLSPEditor.LSPEditorStub stub = (EditorToLSPEditor.LSPEditorStub) EditorToLSPEditor.createStub(
                    definition, uri, extension, projectRoot);
            EditorLanguageServerConnection conn = languageServerEditorListener.editorCreated(stub);
            Assert.assertNotNull(conn);
            Document document = stub.getDocument();
            EditorUtils.runWriteAction(()->{
                document.setText("*** Some error here");
            });
            conn.editorReleased();
        } finally {
            LanguageServerManager.disposeAll();
        }
    }
}
