package robocorp.lsp.intellij.client;

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
            LanguageServerManager.start(definition, ".robot", projectRoot);
        } finally {
            LanguageServerManager.disposeAll();
        }

    }
}
