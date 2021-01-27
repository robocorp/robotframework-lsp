package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.testFramework.fixtures.BasePlatformTestCase;
import org.junit.Test;

public class CompletionTest extends BasePlatformTestCase {
    private static final Logger LOG = Logger.getInstance(CompletionTest.class);

    @Override
    protected void tearDown() throws Exception {
        super.tearDown();
        LanguageServerManager.disposeAll();
    }

    @Override
    protected String getTestDataPath() {
        return "src/test/resources";
    }

    @Test
    public void testVariableCompletion() throws Exception {
        myFixture.configureByFile("casevariable.robot");
        Editor editor = myFixture.getEditor();
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength);
        myFixture.testCompletion("casevariable.robot", "casevariable_after.robot");
    }
}
