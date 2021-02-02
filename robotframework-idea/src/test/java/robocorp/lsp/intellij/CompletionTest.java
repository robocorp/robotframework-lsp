package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import org.eclipse.lsp4j.Diagnostic;
import org.junit.Test;

import java.util.List;

public class CompletionTest extends LSPTesCase {
    private static final Logger LOG = Logger.getInstance(CompletionTest.class);

    @Override
    protected void tearDown() throws Exception {
        super.tearDown();
    }

    @Test
    public void testVariableCompletion() throws Exception {
        myFixture.configureByFile("casevariable.robot");
        Editor editor = myFixture.getEditor();
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength);
        myFixture.testCompletion("casevariable.robot", "casevariable_after.robot");

    }

    @Test
    public void testKeywordsFromLibraries() throws Exception {
        myFixture.configureByFiles("casekeywords.robot", "case1_library.py");
        Editor editor = myFixture.getEditor();
        EditorLanguageServerConnection conn = EditorLanguageServerConnection.getFromUserData(editor);
        final List<Diagnostic> diagnostics = TestUtils.waitForCondition(() -> {
            List<Diagnostic> d = conn.getDiagnostics();
            if (d != null && d.size() > 0) {
                return d;
            }
            return null;
        });
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength);
        myFixture.testCompletion("casekeywords.robot", "casekeywords_after.robot");

    }

    @Test
    public void testKeywordsLibnameDotted() throws Exception {
        myFixture.configureByFiles("case_libname_dotted.robot");
        Editor editor = myFixture.getEditor();
        EditorLanguageServerConnection conn = EditorLanguageServerConnection.getFromUserData(editor);
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength);
        myFixture.testCompletion("case_libname_dotted.robot", "case_libname_dotted_after.robot");
    }
}
