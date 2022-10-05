package robocorp.dap;

import com.intellij.codeInsight.daemon.LineMarkerInfo;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import org.junit.Test;
import robocorp.dap.linemarker.RobotRunnerLineMarkerProvider;
import robocorp.lsp.intellij.LSPTesCase;

import java.util.Arrays;
import java.util.List;

public class RunLineMarkerTest extends LSPTesCase {

    private static final Logger LOG = Logger.getInstance(RunLineMarkerTest.class);

    @Test
    public void testLineMarkerProvider() {
        PsiFile psiFiles = myFixture.configureByFile("caserunlinemarks.robot");
        RobotRunnerLineMarkerProvider provider = new RobotRunnerLineMarkerProvider();
        List<String> caseNames = Arrays.asList("*** Test Cases ***", "First", "Second", "Third", "*** Test Case ***", "Fourth", "Fifth");
        PsiElement[] children = psiFiles.getChildren();
        for (PsiElement item : children) {
            String text = item.getText();
            LineMarkerInfo<?> lineMarkerInfo = provider.getLineMarkerInfo(item);
            if (caseNames.contains(text)) {
                if (lineMarkerInfo == null) {
                    fail("Expected to have a line marker in line with contents: " + text);
                }
            } else {
                if (lineMarkerInfo != null) {
                    fail("Did NOT expect to have a line marker in line with contents: " + text);
                }
            }
        }
    }
}
