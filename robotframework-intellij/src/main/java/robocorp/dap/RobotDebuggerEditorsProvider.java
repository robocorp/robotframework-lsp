package robocorp.dap;

import com.intellij.openapi.fileTypes.FileType;
import com.intellij.openapi.project.Project;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.xdebugger.evaluation.XDebuggerEditorsProviderBase;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.robot.intellij.RobotFrameworkFileType;

/**
 * This is a weird thing in the Intellij framework... apparently it's needed
 * to provide a view of the document when editing breakpoints?!?
 * <p>
 * Why it doesn't use the default language configurations is a bit of a
 * mystery...
 */
public class RobotDebuggerEditorsProvider extends XDebuggerEditorsProviderBase {
    @Override
    public @NotNull FileType getFileType() {
        return RobotFrameworkFileType.INSTANCE;
    }

    @Override
    protected PsiFile createExpressionCodeFragment(@NotNull Project project, @NotNull String text, @Nullable PsiElement context, boolean isPhysical) {
        final String name = "dummy.robot";
        final RobotExpressionCodeFragmentImpl codeFragment = new RobotExpressionCodeFragmentImpl(project, name, text, context, isPhysical);
        return codeFragment;
    }
}
