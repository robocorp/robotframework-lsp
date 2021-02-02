package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import org.eclipse.lsp4j.Diagnostic;
import org.eclipse.lsp4j.ServerCapabilities;
import org.eclipse.lsp4j.TextDocumentSyncKind;
import org.eclipse.lsp4j.TextDocumentSyncOptions;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.junit.Assert;
import org.junit.Test;
import robocorp.robot.intellij.RobotFrameworkLanguage;

import java.util.List;

public class LanguageServerManagerTest extends LSPTesCase {
    private static final Logger LOG = Logger.getInstance(LanguageServerManagerTest.class);

    @Test
    public void testLanguageServerManager() throws Exception {
        LanguageServerDefinition definition = RobotFrameworkLanguage.INSTANCE.getLanguageDefinition();
        myFixture.configureByFiles("case1.robot", "case1_library.py");
        Editor editor = myFixture.getEditor();
        EditorLanguageServerConnection connection = EditorLanguageServerConnection.getFromUserData(editor);
        ServerCapabilities serverCapabilities = connection.getServerCapabilities();
        Either<TextDocumentSyncKind, TextDocumentSyncOptions> textDocumentSync = serverCapabilities.getTextDocumentSync();
        Assert.assertEquals(TextDocumentSyncKind.Incremental, textDocumentSync.getRight().getChange());

        Document document = editor.getDocument();
        EditorUtils.runWriteAction(() -> {
            document.setText("*** Some error here");
        });

        final List<Diagnostic> diagnostics = TestUtils.waitForCondition(() -> {
            List<Diagnostic> d = connection.getDiagnostics();
            if (d != null && d.size() > 0) {
                return d;
            }
            return null;
        });
        Assert.assertEquals(1, diagnostics.size());
        if (!diagnostics.get(0).getMessage().contains("Unrecognized section header '*** Some error here'")) {
            fail("Unexpected message: " + diagnostics.get(0).getMessage());
        }
    }
}
