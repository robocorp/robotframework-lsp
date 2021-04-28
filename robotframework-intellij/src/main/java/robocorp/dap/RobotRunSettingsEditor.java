package robocorp.dap;

import com.intellij.execution.configuration.EnvironmentVariablesComponent;
import com.intellij.openapi.externalSystem.util.ExternalSystemUiUtil;
import com.intellij.openapi.fileChooser.FileChooserDescriptor;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.module.ModuleManager;
import com.intellij.openapi.options.SettingsEditor;
import com.intellij.openapi.project.ProjectUtil;
import com.intellij.openapi.ui.ComponentWithBrowseButton;
import com.intellij.openapi.ui.LabeledComponent;
import com.intellij.openapi.ui.TextComponentAccessor;
import com.intellij.openapi.ui.TextFieldWithBrowseButton;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.ui.RawCommandLineEditor;
import com.intellij.util.Function;
import org.jetbrains.annotations.NotNull;

import javax.swing.*;
import java.awt.*;
import java.util.List;
import java.util.*;
import java.util.stream.Collectors;

/**
 * This is the editor which the user will see to configure the actual launch.
 * <p>
 * It edits the RobotRunProfile options.
 */
public class RobotRunSettingsEditor extends SettingsEditor<RobotRunProfileOptionsEditionAndPersistence> {

    public static final Function<String, List<String>> ARGS_LINE_PARSER = text -> Arrays.asList(ProcessUtils.parseArguments(text));
    public static final Function<List<String>, String> ARGS_LINE_JOINER = strings -> ProcessUtils.getArgumentsAsStr(strings.toArray(new String[0]));

    private LabeledComponent<JComponent> targetRobotLabeledComponent;
    private TextFieldWithBrowseButton targetRobot;
    private ComponentWithBrowseButton.BrowseFolderActionListener targetRobotSelectListener;

    private LabeledComponent argumentsLabeledComponent;
    private RawCommandLineEditor argumentsEditor;

    private LabeledComponent<JComponent> workingDirLabeledComponent;
    private TextFieldWithBrowseButton workingDir;
    private ComponentWithBrowseButton.BrowseFolderActionListener workingDirSelectListener;

    private EnvironmentVariablesComponent envVarsComponent;

    @Override
    protected void resetEditorFrom(@NotNull RobotRunProfileOptionsEditionAndPersistence s) {
        RobotLaunchConfigRunOptions options = s.getOptions();
        String target = options.target;
        targetRobot.setText(target != null ? target : "");

        List<String> args = options.args;
        argumentsEditor.setText(ARGS_LINE_JOINER.fun(args));

        String workDirectory = options.workingDir;
        if (workDirectory == null) {
            workingDir.setText("");
        } else {
            workingDir.setText(workDirectory);
        }

        Map<String, String> environment = options.env;
        if (environment == null) {
            environment = new HashMap<>();
        }
        envVarsComponent.setEnvs(environment);

        // Now, setup action listeners.

        // Compute project roots
        Module[] modules = ModuleManager.getInstance(s.getProject()).getModules();
        final List<VirtualFile> roots = Arrays.stream(modules).map(ProjectUtil::guessModuleDir).collect(Collectors.toList());

        // Set action listener for robot or dir.
        if (targetRobotSelectListener != null) {
            targetRobot.removeActionListener(targetRobotSelectListener);
            targetRobotSelectListener = null;
        }
        FileChooserDescriptor fileChooserDescriptor = new FileChooserDescriptor(true, true, false, false, false, false);
        fileChooserDescriptor.setRoots(roots);
        targetRobotSelectListener = new ComponentWithBrowseButton.BrowseFolderActionListener(
                "Select .robot or folder", null, targetRobot, s.getProject(), fileChooserDescriptor, TextComponentAccessor.TEXT_FIELD_WHOLE_TEXT);
        targetRobot.addActionListener(targetRobotSelectListener);

        // Set action listener for working directory.
        if (workingDirSelectListener != null) {
            workingDir.removeActionListener(workingDirSelectListener);
            workingDirSelectListener = null;
        }
        fileChooserDescriptor = new FileChooserDescriptor(false, true, false, false, false, false);
        fileChooserDescriptor.setRoots(roots);
        workingDirSelectListener = new ComponentWithBrowseButton.BrowseFolderActionListener(
                "Select working directory", null, workingDir, s.getProject(), fileChooserDescriptor, TextComponentAccessor.TEXT_FIELD_WHOLE_TEXT);
        workingDir.addActionListener(workingDirSelectListener);
    }

    @Override
    protected void applyEditorTo(@NotNull RobotRunProfileOptionsEditionAndPersistence s) {
        RobotLaunchConfigRunOptions options = s.getOptions();
        options.target = targetRobot.getText().trim();
        options.args = new ArrayList<>(ARGS_LINE_PARSER.fun(argumentsEditor.getText()));
        options.env = new HashMap<>(envVarsComponent.getEnvs());

        String workingDirText = workingDir.getText().trim();
        if (workingDirText.isEmpty()) {
            options.workingDir = null;

        } else {
            options.workingDir = workingDirText;
        }
    }

    @Override
    protected @NotNull JComponent createEditor() {
        JPanel panel = new JPanel();
        panel.setLayout(new GridBagLayout());

        targetRobotLabeledComponent = new LabeledComponent<>();
        targetRobotLabeledComponent.setText("Target .robot or folder to run");
        targetRobot = new TextFieldWithBrowseButton();
        targetRobotLabeledComponent.setComponent(targetRobot);
        panel.add(targetRobotLabeledComponent, ExternalSystemUiUtil.getFillLineConstraints(0));

        argumentsLabeledComponent = new LabeledComponent();
        argumentsLabeledComponent.setText("Arguments");
        argumentsEditor = new RawCommandLineEditor(ARGS_LINE_PARSER, ARGS_LINE_JOINER);
        argumentsLabeledComponent.setComponent(argumentsEditor);
        panel.add(argumentsLabeledComponent, ExternalSystemUiUtil.getFillLineConstraints(0));

        workingDirLabeledComponent = new LabeledComponent<>();
        workingDirLabeledComponent.setText("Working directory");
        workingDir = new TextFieldWithBrowseButton();
        workingDirLabeledComponent.setComponent(workingDir);
        panel.add(workingDirLabeledComponent, ExternalSystemUiUtil.getFillLineConstraints(0));

        envVarsComponent = new EnvironmentVariablesComponent();
        panel.add(envVarsComponent, ExternalSystemUiUtil.getFillLineConstraints(0));

        return panel;
    }
}
