package robocorp.dap.stack;

import com.intellij.icons.AllIcons;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.xdebugger.frame.*;
import org.eclipse.lsp4j.debug.Scope;
import org.jetbrains.annotations.NotNull;
import robocorp.dap.RobotDebugProcess;

public class DAPDebugScope extends XNamedValue {
    private static final Logger LOG = Logger.getInstance(DAPDebugScope.class);
    private final Scope scope;
    private final RobotDebugProcess robotDebugProcess;

    public DAPDebugScope(Scope s, RobotDebugProcess robotDebugProcess) {
        super(s.getName());
        this.scope = s;
        this.robotDebugProcess = robotDebugProcess;
    }

    public Scope getScope() {
        return scope;
    }

    @Override
    public void computePresentation(@NotNull XValueNode node, @NotNull XValuePlace place) {
        node.setPresentation(AllIcons.Debugger.Value, null, scope.getName(), true);
    }

    @Override
    public void computeChildren(@NotNull XCompositeNode node) {
        if (node.isObsolete()) {
            return;
        }
        ApplicationManager.getApplication().executeOnPooledThread(() -> {
            try {
                if (!node.isObsolete()) {
                    XValueChildrenList values = robotDebugProcess.loadVariablesFromScope(this);
                    node.addChildren(values, true);
                }
            } catch (Exception e) {
                if (!node.isObsolete()) {
                    node.setErrorMessage("Error: unable to display variables from scope.");
                }
                LOG.warn(e);
            }
        });

    }
}
