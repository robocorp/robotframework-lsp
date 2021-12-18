package robocorp.dap;

import com.intellij.execution.configurations.LocatableRunConfigurationOptions;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.ide.macro.Macro;
import com.intellij.ide.macro.MacroManager;
import com.intellij.openapi.actionSystem.DataContext;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.util.NlsSafe;

import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * These are the launch configuration options that the user can customize.
 */
public class RobotLaunchConfigRunOptions extends LocatableRunConfigurationOptions {
    private static Logger LOG = Logger.getInstance(RobotLaunchConfigRunOptions.class);

    public String target;
    public List<String> args;
    public Map<String, String> env;
    public String workingDir;
    public boolean makeSuite = true;

    public String computeWorkingDir() {
        if (workingDir == null) {
            if (target != null && !target.isEmpty()) {
                return new File(target).getParent();
            }
        }
        return workingDir;
    }

    private @NlsSafe String expandMacrosInStr(ExecutionEnvironment executionEnvironment, String str) {
        if (executionEnvironment != null) {
            DataContext context = executionEnvironment.getDataContext();
            if (str != null && str.contains("$")) {
                try {
                    return MacroManager.getInstance().expandMacrosInString(str, true, context);
                } catch (Macro.ExecutionCancelledException e) {
                    LOG.info(e);
                }
            }
            return str;
        }
        return str;
    }

    public RobotLaunchConfigRunOptions getWithVarsExpanded(ExecutionEnvironment executionEnvironment) {
        RobotLaunchConfigRunOptions options = new RobotLaunchConfigRunOptions();
        if (this.target != null) {
            options.target = expandMacrosInStr(executionEnvironment, this.target);
        }

        if (this.args != null) {
            ArrayList<String> lst = new ArrayList<>(this.args.size());
            for (String s : this.args) {
                lst.add(expandMacrosInStr(executionEnvironment, s));
            }
            options.args = lst;
        }

        if (this.env != null) {
            Map<String, String> env = new HashMap<>(this.env.size());
            for (Map.Entry<String, String> entry : this.env.entrySet()) {
                env.put(entry.getKey(), expandMacrosInStr(executionEnvironment, entry.getValue()));
            }
            options.env = env;
        }

        if (this.workingDir != null) {
            options.workingDir = expandMacrosInStr(executionEnvironment, this.workingDir);
        }

        options.makeSuite = this.makeSuite;
        return options;
    }

}
