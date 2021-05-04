package robocorp.dap;

import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.xdebugger.breakpoints.SuspendPolicy;
import com.intellij.xdebugger.breakpoints.XLineBreakpointTypeBase;
import org.jetbrains.annotations.NotNull;
import robocorp.lsp.intellij.EditorUtils;
import robocorp.lsp.intellij.LanguageServerDefinition;

/**
 * Class that configures a breakpoint for robot framework.
 * <p>
 * It must also be registered in the plugin.xml.
 * <p>
 * Apparently, what Intellij does when a breakpoint is added is collect
 * all the breakpoint classes registered in the plugin, instantiate all
 * of them for the breakpoint and then check if `canPutAt` is valid
 * (and if it is the breakpoint is created).
 * <p>
 * Later on the `XDebugProcess` implementation must provide subclasses of
 * `XBreakpointHandler` in `getBreakpointHandlers`, which is responsible
 * to actually handle a registered breakpoint and send it to the debugger
 * backend.
 */
public class RobotLineBreakpoint extends XLineBreakpointTypeBase {
    public static final String ID = "robot-line";

    protected RobotLineBreakpoint() {
        super(ID, "Robot Line Breakpoint", new RobotDebuggerEditorsProvider());
    }

    @Override
    public boolean canPutAt(@NotNull VirtualFile file, int line, @NotNull Project project) {
        if (file.getName().endsWith(".py")) {
            return true;
        }
        LanguageServerDefinition languageDefinition = EditorUtils.getLanguageDefinition(file, project);
        if (languageDefinition != null && languageDefinition.ext.contains(".robot")) {
            return true;
        }
        return false;
    }

    @Override
    public boolean isSuspendThreadSupported() {
        return false;
    }

    @Override
    public SuspendPolicy getDefaultSuspendPolicy() {
        return SuspendPolicy.ALL;
    }
}
