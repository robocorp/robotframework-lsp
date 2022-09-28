package robocorp.dap.linemarker;

import com.intellij.execution.*;
import com.intellij.execution.configurations.RunConfiguration;
import com.intellij.execution.executors.DefaultDebugExecutor;
import com.intellij.execution.executors.DefaultRunExecutor;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.execution.runners.ExecutionEnvironmentBuilder;
import com.intellij.icons.AllIcons;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.project.ProjectManager;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.dap.RobotConfigurationFactory;
import robocorp.dap.RobotConfigurationType;
import robocorp.dap.RobotLaunchConfigRunOptions;
import robocorp.dap.RobotRunProfileOptionsEditionAndPersistence;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class RobotRunAction extends AnAction {
    private static final RobotConfigurationFactory FACTORY = new RobotConfigurationFactory(new RobotConfigurationType());
    private final String name;
    private final boolean isDebug;

    /**
     * The name may be null if this is a test suite run.
     */
    public RobotRunAction(@Nullable String name, boolean isDebug) {
        super(getActionText(name, isDebug), getActionDescription(name, isDebug), isDebug ? AllIcons.Actions.StartDebugger : AllIcons.RunConfigurations.TestState.Run);
        this.name = name;
        this.isDebug = isDebug;
    }

    private static String getActionDescription(String name, boolean isDebug) {
        return getActionText(name, isDebug);
    }

    private static String getActionText(String name, boolean isDebug) {
        if (name == null) {
            return isDebug ? "Debug Suite" : "Run Suite";
        }
        return isDebug ? "Debug: " + name : "Run: " + name;
    }

    @Override
    public void actionPerformed(@NotNull AnActionEvent e) {
        Project project = ProjectManager.getInstance().getOpenProjects()[0];
        RunConfiguration runConfiguration = FACTORY.createTemplateConfiguration(project);

        RobotRunProfileOptionsEditionAndPersistence options = (RobotRunProfileOptionsEditionAndPersistence) runConfiguration;
        RobotLaunchConfigRunOptions runOptions = options.getOptions();

        List<String> args = new ArrayList<>();
        // file
        runOptions.target = "$FilePath$";
        // work dir
        runOptions.workingDir = "$ProjectFileDir$";

        // log and case
        args.add("-d");
        args.add("$ProjectFileDir$/log");
        // if name is null then run this file
        if (name == null) {
            runConfiguration.setName("run current file");
        } else {
            runConfiguration.setName("run [" + name + "]");
            args.add("-t");
            args.add(name);
        }
        runOptions.args = args;

        // console encoding set utf-8
        Map<String, String> env = new HashMap<>();
        env.put("PYTHONIOENCODING", "utf-8");
        runOptions.env = env;

        RunnerAndConfigurationSettings newConfig = RunManager.getInstance(project).createConfiguration(runConfiguration, FACTORY);
        ExecutionEnvironment executionEnvironment;
        try {
            Executor runExecutorInstance = isDebug ? DefaultDebugExecutor.getDebugExecutorInstance() : DefaultRunExecutor.getRunExecutorInstance();
            executionEnvironment = ExecutionEnvironmentBuilder.create(runExecutorInstance, newConfig).dataContext(e.getDataContext()).build();
        } catch (ExecutionException ex) {
            throw new RuntimeException(ex);
        }
        ProgramRunnerUtil.executeConfiguration(executionEnvironment, true, true);
    }

    public String getName() {
        return name;
    }
}
