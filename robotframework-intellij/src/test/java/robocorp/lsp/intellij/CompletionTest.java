package robocorp.lsp.intellij;

import com.intellij.codeInsight.lookup.AutoCompletionPolicy;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import org.eclipse.lsp4j.Diagnostic;
import org.junit.Test;

import java.util.List;

public class CompletionTest extends LSPTesCase {
    private static final Logger LOG = Logger.getInstance(CompletionTest.class);

    @Override
    protected void setUp() throws Exception {
        super.setUp();
        FeatureCodeCompletion.AUTO_COMPLETION_POLICY = AutoCompletionPolicy.ALWAYS_AUTOCOMPLETE;
    }

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
    public void testVariableCompletion2() throws Exception {
        myFixture.configureByFile("casevariable2.robot");
        Editor editor = myFixture.getEditor();
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength - "}   ${DUMMY_VAR1}".length());
        myFixture.testCompletion("casevariable2.robot", "casevariable2_after.robot");
    }

    @Test
    public void testKeywordsFromLibraries() throws Exception {
        myFixture.configureByFiles("casekeywords.robot", "case1_library.py");
        Editor editor = myFixture.getEditor();
        EditorLanguageServerConnection conn = EditorLanguageServerConnection.getFromUserData(editor);
        waitForDiagnostic(conn);
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength);
        myFixture.testCompletion("casekeywords.robot", "casekeywords_after.robot");

    }

    private List<Diagnostic> waitForDiagnostic(EditorLanguageServerConnection conn) {
        final List<Diagnostic> diagnostics = TestUtils.waitForCondition(() -> {
            List<Diagnostic> d = conn.getDiagnostics();
            if (d != null && d.size() > 0) {
                return d;
            }
            return null;
        });
        return diagnostics;
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

    @Test
    public void testCompleteDollarSign() throws Exception {
        myFixture.configureByFiles("case_keyword_with_args.robot");
        Editor editor = myFixture.getEditor();
        EditorLanguageServerConnection conn = EditorLanguageServerConnection.getFromUserData(editor);
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength);
        myFixture.testCompletion("case_keyword_with_args.robot", "case_keyword_with_args_after.robot");
    }

    @Test
    public void testCompleteAtSign() throws Exception {
        myFixture.configureByFiles("case_keyword_args_at.robot");
        Editor editor = myFixture.getEditor();
        EditorLanguageServerConnection conn = EditorLanguageServerConnection.getFromUserData(editor);
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength);
        myFixture.testCompletion("case_keyword_args_at.robot", "case_keyword_args_at_after.robot");
    }

    @Test
    public void testCompleteResourceName() throws Exception {
        myFixture.configureByFiles("sub/case_sub.robot", "case_keyword_with_args_after.robot");
        Editor editor = myFixture.getEditor();
        EditorLanguageServerConnection conn = EditorLanguageServerConnection.getFromUserData(editor);
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength);
        myFixture.testCompletion("sub/case_sub.robot", "sub/case_sub_after.robot");
    }

    @Test
    public void testCompleteForEnumerate() throws Exception {
        myFixture.configureByFiles("case_for_complete.robot");
        Editor editor = myFixture.getEditor();
        EditorLanguageServerConnection conn = EditorLanguageServerConnection.getFromUserData(editor);
        waitForDiagnostic(conn);
        int textLength = editor.getDocument().getTextLength();
        editor.getCaretModel().moveToOffset(textLength);
        myFixture.testCompletion("case_for_complete.robot", "case_for_complete_after.robot");
    }

}
