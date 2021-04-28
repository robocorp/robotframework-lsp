package robocorp.dap;

import com.intellij.openapi.project.Project;
import com.intellij.psi.FileViewProvider;
import com.intellij.psi.PsiElement;
import com.intellij.psi.SingleRootFileViewProvider;
import com.intellij.psi.impl.PsiManagerEx;
import com.intellij.psi.impl.file.impl.FileManager;
import com.intellij.psi.impl.source.PsiFileImpl;
import com.intellij.psi.impl.source.tree.FileElement;
import com.intellij.testFramework.LightVirtualFile;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.robot.intellij.RobotFrameworkFileType;
import robocorp.robot.intellij.RobotFrameworkLanguage;
import robocorp.robot.intellij.RobotPsiFile;

/**
 * This is a weird thing in the Intellij framework... apparently it's needed
 * to provide a view of the document when editing breakpoints?!?
 * <p>
 * Why it doesn't use the default language configurations is a bit of a
 * mystery...
 */
public class RobotExpressionCodeFragmentImpl extends RobotPsiFile {

    private boolean isPhysical;
    private PsiElement context;
    private FileViewProvider viewProvider;

    public RobotExpressionCodeFragmentImpl(Project project, @NonNls String name, CharSequence text, @Nullable PsiElement context, boolean isPhysical) {
        super(PsiManagerEx.getInstanceEx(project).getFileManager().createFileViewProvider(
                new LightVirtualFile(name, RobotFrameworkFileType.INSTANCE, text), isPhysical), RobotFrameworkLanguage.INSTANCE
        );
        this.context = context;
        this.isPhysical = isPhysical;
    }

    @Override
    public boolean isPhysical() {
        return isPhysical;
    }

    @Override
    public PsiElement getContext() {
        return context != null && context.isValid() ? context : super.getContext();
    }

    @Override
    @NotNull
    public FileViewProvider getViewProvider() {
        if (viewProvider != null) {
            return viewProvider;
        }
        return super.getViewProvider();
    }

    @Override
    protected PsiFileImpl clone() {
        final RobotExpressionCodeFragmentImpl clone = (RobotExpressionCodeFragmentImpl) cloneImpl((FileElement) calcTreeElement().clone());
        clone.isPhysical = false;
        clone.myOriginalFile = this;
        FileManager fileManager = ((PsiManagerEx) getManager()).getFileManager();
        SingleRootFileViewProvider cloneViewProvider = (SingleRootFileViewProvider) fileManager.createFileViewProvider(new LightVirtualFile(getName(), getLanguage(), getText()), false);
        cloneViewProvider.forceCachedPsi(clone);
        clone.viewProvider = cloneViewProvider;
        return clone;
    }
}
