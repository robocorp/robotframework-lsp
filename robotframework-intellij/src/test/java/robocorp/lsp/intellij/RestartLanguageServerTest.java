package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import org.eclipse.lsp4j.Diagnostic;
import org.eclipse.lsp4j.ExecuteCommandParams;
import org.junit.Assert;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

public class RestartLanguageServerTest extends LSPTesCase {
    private static final Logger LOG = Logger.getInstance(RestartLanguageServerTest.class);

    @Test
    public void testRestart() throws Exception {
        myFixture.configureByFile("case1.robot");
        Editor editor = myFixture.getEditor();
        Document document = editor.getDocument();
        EditorUtils.runWriteAction(() -> {
            document.setText("*** Keywords ***\n" +
                    "My Equal Redefined\n" +
                    "    [Arguments]         ${arg1}     ${arg2}\n" +
                    "    Should Be Equal     ${arg1}     ${arg2}\n" +
                    "\n" +
                    "*** Test Cases ***\n" +
                    "Call Equal Redefined\n" +
                    "    Error not defined");
        });
        EditorLanguageServerConnection conn = EditorLanguageServerConnection.getFromUserData(editor);
        final List<Diagnostic> diagnostics = TestUtils.waitForCondition(() -> {
            List<Diagnostic> d = conn.getDiagnostics();
            if (d != null && d.size() > 0) {
                return d;
            }
            return null;
        });
        verifyInternalInfo(conn);

        // Ok, disposed of all. We should auto-restart when needed.
        LanguageServerManager.shutdownAll();

        verifyInternalInfo(conn);
    }

    private void verifyInternalInfo(EditorLanguageServerConnection conn) throws InterruptedException, java.util.concurrent.ExecutionException, java.util.concurrent.TimeoutException {
        LanguageServerCommunication languageServerCommunication = conn.getLanguageServerCommunication();
        CompletableFuture<Object> future = languageServerCommunication.command(new ExecuteCommandParams("robot.getInternalInfo", new ArrayList<>()));
        Map<Object, Object> o = (Map) future.get(4, TimeUnit.SECONDS);
        LOG.info(o.toString());
        Assert.assertEquals("{}", o.get("settings").toString());
        List<Object> inMemoryDocs = (List<Object>) o.get("in_memory_docs");
        Assert.assertEquals(1, inMemoryDocs.size());
    }
}
