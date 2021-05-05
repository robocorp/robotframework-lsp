package robocorp.dap;

import com.intellij.execution.configurations.LocatableRunConfigurationOptions;

import java.io.File;
import java.util.List;
import java.util.Map;

/**
 * These are the launch configuration options that the user can customize.
 */
public class RobotLaunchConfigRunOptions extends LocatableRunConfigurationOptions {
    public String target;
    public List<String> args;
    public Map<String, String> env;
    public String workingDir;

    public String computeWorkingDir() {
        if (workingDir == null) {
            if (target != null && !target.isEmpty()) {
                return new File(target).getParent();
            }
        }
        return workingDir;
    }
}
