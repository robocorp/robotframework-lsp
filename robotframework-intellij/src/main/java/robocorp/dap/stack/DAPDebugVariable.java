package robocorp.dap.stack;

import com.intellij.icons.AllIcons;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.xdebugger.frame.*;
import org.eclipse.lsp4j.debug.Variable;
import org.jetbrains.annotations.NotNull;
import robocorp.dap.RobotDebugProcess;

public class DAPDebugVariable extends XNamedValue {
    private static final Logger LOG = Logger.getInstance(DAPDebugVariable.class);
    private final Variable variable;
    private final RobotDebugProcess robotDebugProcess;

    public DAPDebugVariable(Variable variable, RobotDebugProcess robotDebugProcess) {
        super(variable.getName());
        this.variable = variable;
        this.robotDebugProcess = robotDebugProcess;
    }

    public Variable getVariable() {
        return variable;
    }

    @Override
    public void computePresentation(@NotNull XValueNode node, @NotNull XValuePlace place) {
        boolean hasChildren = this.variable.getVariablesReference() > 0;
        node.setPresentation(hasChildren ? AllIcons.Debugger.Value : AllIcons.Debugger.Db_primitive, null, variable.getValue(), hasChildren);
    }

    @Override
    public void computeChildren(@NotNull XCompositeNode node) {
        if (node.isObsolete()) {
            return;
        }
        ApplicationManager.getApplication().executeOnPooledThread(() -> {
            try {
                if (!node.isObsolete()) {
                    XValueChildrenList values = robotDebugProcess.loadVariablesFromVariable(this);
                    node.addChildren(values, true);
                }
            } catch (Exception e) {
                if (!node.isObsolete()) {
                    node.setErrorMessage("Error: unable to display variables under variable.");
                }
                LOG.warn(e);
            }
        });

    }

}
