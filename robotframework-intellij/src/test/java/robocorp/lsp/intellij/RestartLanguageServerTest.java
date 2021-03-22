package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import org.eclipse.lsp4j.Diagnostic;
import org.eclipse.lsp4j.ExecuteCommandParams;
import org.junit.Assert;
import org.junit.Test;
import robocorp.robot.intellij.RobotPreferences;

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
        TestUtils.waitForCondition(() -> {
            List<Diagnostic> d = conn.getDiagnostics();
            if (d != null && d.size() > 0) {
                return d;
            }
            return null;
        });
        long pid = verifyInternalInfo(conn);

        // Ok, disposed of all. We should auto-restart when needed.
        LanguageServerManager.shutdownAll();

        long newPid = verifyInternalInfo(conn);
        Assert.assertNotEquals(pid, newPid);

        // Ok, we've been able to restart properly, now, let's change the settings so
        // that the python executable is invalid (and thus it should be impossible to
        // restart).
        RobotPreferences robotPreferences = RobotPreferences.getInstance();
        try {
            EditorUtils.ignoreLogErrors += 1;
            robotPreferences.setRobotLanguageServerPython("/wrong/executable");

            LanguageServerCommunication languageServerCommunication = conn.getLanguageServerCommunication();
            CompletableFuture<Object> future = languageServerCommunication.command(new ExecuteCommandParams("robot.getInternalInfo", new ArrayList<>()));
            Assert.assertNull(future);
            Assert.assertEquals(0, languageServerCommunication.getCrashCount()); // Note: we don't even try to start because the settings are invalid.
            robotPreferences.setRobotLanguageServerPython(""); // reset to default
        } finally {
            EditorUtils.ignoreLogErrors -= 1;
        }

        verifyInternalInfo(conn);

    }

    private long verifyInternalInfo(EditorLanguageServerConnection conn) throws InterruptedException, java.util.concurrent.ExecutionException, java.util.concurrent.TimeoutException {
        LanguageServerCommunication languageServerCommunication = conn.getLanguageServerCommunication();
        CompletableFuture<Object> future = languageServerCommunication.command(new ExecuteCommandParams("robot.getInternalInfo", new ArrayList<>()));
        Map<Object, Object> o = (Map) future.get(4, TimeUnit.SECONDS);
        LOG.info(o.toString());
        Assert.assertEquals("{}", o.get("settings").toString());
        List<Object> inMemoryDocs = (List<Object>) o.get("inMemoryDocs");
        Assert.assertEquals(1, inMemoryDocs.size());
        return ((Double) o.get("processId")).longValue();
    }
}
