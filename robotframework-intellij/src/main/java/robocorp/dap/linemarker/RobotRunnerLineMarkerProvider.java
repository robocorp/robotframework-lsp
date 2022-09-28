package robocorp.dap.linemarker;

import com.intellij.codeInsight.daemon.LineMarkerInfo;
import com.intellij.codeInsight.daemon.LineMarkerProvider;
import com.intellij.codeInsight.daemon.MergeableLineMarkerInfo;
import com.intellij.icons.AllIcons;
import com.intellij.openapi.actionSystem.ActionGroup;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.DefaultActionGroup;
import com.intellij.openapi.editor.markup.GutterIconRenderer;
import com.intellij.openapi.util.TextRange;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.psi.tree.IElementType;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.FastStringBuffer;
import robocorp.lsp.psi.LSPPsiAstElement;
import robocorp.robot.intellij.RobotElementType;
import robocorp.robot.intellij.RobotPsiFile;

import javax.swing.*;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class RobotRunnerLineMarkerProvider implements LineMarkerProvider {
    private static final String ROBOT_FILE_SUFFIX = ".robot";
    private static final Set<String> ROBOT_TEST_CASE_NAME = new HashSet<>(Arrays.asList("test case", "test cases", "task", "tasks"));

    @Override
    public LineMarkerInfo<?> getLineMarkerInfo(@NotNull final PsiElement element) {
        PsiFile file = element.getContainingFile();
        // is root or isn't .robot
        if (!(file instanceof RobotPsiFile) || !file.getName().endsWith(ROBOT_FILE_SUFFIX) || !(element instanceof LSPPsiAstElement)) {
            return null;
        }
        String text = element.getText().strip();
        // text is empty or is leaf node
        if (text.length() == 0 || element.getFirstChild() == null) {
            return null;
        }
        if (isTestCaseElement(element)) {
            return new RobotRunnerLineMarkerProvider.RobotRunLineMarkerInfo(element.getFirstChild(), null, element.getTextRange());
        }

        // We only match the first token after a new line.
        if (element.getNode().getElementType() != RobotElementType.DEFAULT) {
            return null;
        }

        PsiElement prev = element.getPrevSibling();
        if (prev == null || !RobotElementType.NEW_LINE.equals(prev.getNode().getElementType())) {
            return null;
        }

        // Search for test case
        for (; prev != null; prev = prev.getPrevSibling()) {
            IElementType elementType = prev.getNode().getElementType();
            // Find previous heading and see if it was a test case/task (if it was we're in a test, otherwise we're not).
            if (elementType != RobotElementType.HEADING) {
                continue;
            }
            if (isTestCaseElement(prev)) {
                PsiElement child = element.getFirstChild();
                return new RobotRunnerLineMarkerProvider.RobotRunLineMarkerInfo(child, getCaseName(child), getCaseTextRange(child));
            } else {
                return null;
            }
        }
        return null;
    }

    public static String getCaseName(PsiElement element) {
        FastStringBuffer sb = new FastStringBuffer(50);
        for (element = element.getParent(); element != null && !RobotElementType.NEW_LINE.equals(element.getNode().getElementType()); element = element.getNextSibling()) {
            sb.append(element.getText());
        }
        sb.replaceAll('*', ' ');
        sb.trim();
        return sb.toString();
    }

    public static TextRange getCaseTextRange(PsiElement element) {
        int start = -1;
        int end = -1;
        for (element = element.getParent(); element != null && !RobotElementType.NEW_LINE.equals(element.getNode().getElementType()); element = element.getNextSibling()) {
            TextRange textRange = element.getTextRange();
            if (textRange.getStartOffset() < start || start == -1) {
                start = textRange.getStartOffset();
            }
            if (textRange.getEndOffset() > end || end == -1) {
                end = textRange.getEndOffset();
            }
        }
        if (start != -1 && end != -1) {
            return new TextRange(start, end);
        }
        return element.getTextRange();
    }

    private boolean isTestCaseElement(@NotNull PsiElement element) {
        IElementType elementType = element.getNode().getElementType();
        if (elementType != RobotElementType.HEADING) {
            return false;
        }

        String text = element.getText().replace('*', ' ').toLowerCase().trim();
        return ROBOT_TEST_CASE_NAME.contains(text);
    }

    static class RobotRunLineMarkerInfo extends MergeableLineMarkerInfo<PsiElement> {

        private final String testName;

        public RobotRunLineMarkerInfo(@NotNull PsiElement element, String testName, TextRange textRange) {
            super(element, textRange, AllIcons.RunConfigurations.TestState.Run, (e) -> {
                if (testName == null) {
                    return "Run Suite";
                } else {
                    return "Run " + testName;
                }
            }, null, GutterIconRenderer.Alignment.CENTER, () -> RobotRunnerLineMarkerProvider.getCaseName(element));
            this.testName = testName;
        }

        @Override
        public GutterIconRenderer createGutterRenderer() {
            return new LineMarkerGutterIconRenderer<>(this) {
                private RobotRunAction robotRunAction;
                private DefaultActionGroup actionGroup;

                @Override
                public AnAction getClickAction() {
                    if (robotRunAction != null) {
                        return robotRunAction;
                    }
                    robotRunAction = new RobotRunAction(testName, false);
                    return robotRunAction;
                }

                @Override
                public @Nullable ActionGroup getPopupMenuActions() {
                    if (actionGroup != null) {
                        return actionGroup;
                    }
                    actionGroup = new DefaultActionGroup("Run...", true);
                    actionGroup.addAction(new RobotRunAction(testName, false));
                    actionGroup.addAction(new RobotRunAction(testName, true)).setAsSecondary(true);
                    return actionGroup;
                }
            };
        }

        @Override
        public boolean canMergeWith(@NotNull MergeableLineMarkerInfo<?> info) {
            return true;
        }

        @Override
        public Icon getCommonIcon(@NotNull List<? extends MergeableLineMarkerInfo<?>> infos) {
            return AllIcons.RunConfigurations.TestState.Run;
        }
    }

}

