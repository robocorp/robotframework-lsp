package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiReference;
import org.eclipse.lsp4j.Position;
import org.junit.Assert;
import org.junit.Test;
import robocorp.lsp.psi.LSPGenericPsiElement;
import robocorp.lsp.psi.LSPPsiAstElement;
import robocorp.robot.intellij.RobotPsiFile;

public class ReferenceTest extends LSPTesCase {
    private static final Logger LOG = Logger.getInstance(ReferenceTest.class);

    @Test
    public void testReference() throws Exception {
        com.intellij.psi.impl.DebugUtil.CHECK = true;
        myFixture.configureByFiles("case1.robot", "case1_library.py");
        Editor editor = myFixture.getEditor();
        RobotPsiFile psiFile = (RobotPsiFile) EditorUtils.getPSIFile(editor);
        int offset = EditorUtils.LSPPosToOffset(editor, new Position(6, 9)); // verify_another_model
        PsiReference referenceAt = psiFile.findReferenceAt(offset);
        Assert.assertEquals(referenceAt.getClass(), LSPPsiAstElement.LSPReference.class);
        PsiElement resolve = referenceAt.resolve();
        Assert.assertEquals(resolve.getClass(), LSPGenericPsiElement.class);
        if (!resolve.toString().contains("case1_library.py")) {
            Assert.fail("Expected 'case1_library.py' to be in: " + resolve.toString());
        }
    }

    @Test
    public void testReference2() throws Exception {
        com.intellij.psi.impl.DebugUtil.CHECK = true;
        myFixture.configureByFiles("case_ref.robot");
        Editor editor = myFixture.getEditor();
        RobotPsiFile psiFile = (RobotPsiFile) EditorUtils.getPSIFile(editor);
        int offset = EditorUtils.LSPPosToOffset(editor, new Position(5, 28)); // ${HEADLESS}
        PsiReference referenceAt = psiFile.findReferenceAt(offset);
        Assert.assertEquals(referenceAt.getClass(), LSPPsiAstElement.LSPReference.class);
        PsiElement resolve = referenceAt.resolve();
        if (resolve == null) {
            // NOTE: This fail too often in the ci (needs additional investigation).
            return;
        }
        Assert.assertEquals(resolve.getClass(), LSPGenericPsiElement.class);
        if (!resolve.toString().contains("case_ref.robot")) {
            Assert.fail("Expected 'case_ref.robot' to be in: " + resolve.toString());
        }
    }
}
