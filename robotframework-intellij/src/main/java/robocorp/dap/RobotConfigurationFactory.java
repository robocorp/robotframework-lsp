package robocorp.dap;

import com.intellij.execution.configurations.ConfigurationFactory;
import com.intellij.execution.configurations.RunConfiguration;
import com.intellij.openapi.components.BaseState;
import com.intellij.openapi.project.Project;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/**
 * Glue to notify of the robot framework launch configuration type.
 *
 * Also see: RobotConfigurationType
 */
public class RobotConfigurationFactory extends ConfigurationFactory {

    public RobotConfigurationFactory(RobotConfigurationType robotConfigurationType) {
        super(robotConfigurationType);
    }

    @Override
    public @NotNull RunConfiguration createTemplateConfiguration(@NotNull Project project) {
        return new RobotRunProfileOptionsEditionAndPersistence(project, this, "RobotFramework");
    }

    @Override
    public @NotNull String getName() {
        return "RobotFramework";
    }

    @Override
    public @NotNull
    @NonNls
    String getId() {
        return "RobotFramework";
    }

    @Override
    public @Nullable Class<? extends BaseState> getOptionsClass() {
        return RobotLaunchConfigRunOptions.class;
    }
}
