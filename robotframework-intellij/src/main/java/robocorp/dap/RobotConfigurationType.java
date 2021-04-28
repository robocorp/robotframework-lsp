package robocorp.dap;

import com.intellij.execution.configurations.ConfigurationFactory;
import com.intellij.execution.configurations.ConfigurationType;
import org.jetbrains.annotations.Nls;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import robocorp.robot.intellij.RobotFrameworkIcons;

import javax.swing.*;

/**
 * Glue to notify of the robot framework launch configuration type.
 * <p>
 * Also see: RobotConfigurationFactory
 */
public class RobotConfigurationType implements ConfigurationType {
    @Override
    public @NotNull @Nls(capitalization = Nls.Capitalization.Title) String getDisplayName() {
        return "Robot Framework";
    }

    @Override
    public @Nls(capitalization = Nls.Capitalization.Sentence) String getConfigurationTypeDescription() {
        return "Runs Robot Framework using the Debug Adapter Protocol";
    }

    @Override
    public Icon getIcon() {
        return RobotFrameworkIcons.FILE;
    }

    @Override
    public @NotNull
    @NonNls
    String getId() {
        return "RobotFramework";
    }

    @Override
    public ConfigurationFactory[] getConfigurationFactories() {
        return new ConfigurationFactory[]{new RobotConfigurationFactory(this)};
    }
}
