package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiReference;
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
        PsiReference referenceAt = psiFile.findReferenceAt(40);
        Assert.assertEquals(referenceAt.getClass(), LSPPsiAstElement.LSPReference.class);
        PsiElement resolve = referenceAt.resolve();
        Assert.assertEquals(resolve.getClass(), LSPGenericPsiElement.class);
        if (!resolve.toString().contains("case1_library.py")) {
            Assert.fail("Expected 'case1_library.py' to be in: " + resolve.toString());
        }
    }
}
