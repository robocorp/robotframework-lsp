package robocorp.dap;

import com.intellij.execution.ExecutionException;
import com.intellij.execution.Executor;
import com.intellij.execution.configurations.LocatableConfigurationBase;
import com.intellij.execution.configurations.RunConfiguration;
import com.intellij.execution.configurations.RunProfileState;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.openapi.options.SettingsEditor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.InvalidDataException;
import com.intellij.util.xmlb.SerializationFilter;
import com.intellij.util.xmlb.XmlSerializer;
import org.jdom.Element;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/**
 * This class exists as a glue to provide the editor for the launch configuration options
 * and to persist the options so that it's properly restored later on.
 */
public class RobotRunProfileOptionsEditionAndPersistence extends LocatableConfigurationBase {

    public RobotRunProfileOptionsEditionAndPersistence(Project project, RobotConfigurationFactory factory, String name) {
        super(project, factory, name);
    }

    @Override
    public @NotNull SettingsEditor<? extends RunConfiguration> getConfigurationEditor() {
        return new RobotRunSettingsEditor();
    }

    @Override
    public @Nullable RunProfileState getState(@NotNull Executor executor, @NotNull ExecutionEnvironment environment) throws ExecutionException {
        return new RobotRunProfileStateRobotDAPStarter(environment);
    }

    @Override
    public @NotNull RobotLaunchConfigRunOptions getOptions() {
        return (RobotLaunchConfigRunOptions) super.getOptions();
    }

    @Override
    public void readExternal(@NotNull Element element) throws InvalidDataException {
        super.readExternal(element);

        XmlSerializer.deserializeInto(this.getOptions(), element);
    }

    @Override
    public void writeExternal(@NotNull Element element) {
        super.writeExternal(element);

        @Nullable SerializationFilter serializationFilter = (accessor, bean) -> {
            String name = accessor.getName();
            switch (name) {
                case "target":
                case "args":
                case "env":
                case "workingDir":
                case "makeSuite":
                    return true;
            }
            return false;
        };
        XmlSerializer.serializeInto(this.getOptions(), element, serializationFilter);
    }
}
