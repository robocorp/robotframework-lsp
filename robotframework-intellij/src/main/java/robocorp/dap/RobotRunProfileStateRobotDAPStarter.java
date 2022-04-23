package robocorp.dap;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import com.intellij.execution.ExecutionException;
import com.intellij.execution.configurations.CommandLineState;
import com.intellij.execution.configurations.GeneralCommandLine;
import com.intellij.execution.configurations.ParametersList;
import com.intellij.execution.configurations.RunProfile;
import com.intellij.execution.process.KillableColoredProcessHandler;
import com.intellij.execution.process.ProcessHandler;
import com.intellij.execution.process.ProcessWrapper;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.execution.ui.ConsoleView;
import com.intellij.execution.ui.ConsoleViewContentType;
import com.intellij.execution.ui.RunContentDescriptor;
import com.intellij.execution.ui.RunContentManager;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.project.Project;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.LanguageServerDefinition;
import robocorp.robot.intellij.CancelledException;
import robocorp.robot.intellij.RobotFrameworkLanguage;
import robocorp.robot.intellij.RobotPreferences;

import java.io.*;
import java.nio.charset.Charset;
import java.util.Map;

/**
 * This is the class responsible for starting the debug adapter.
 */
public class RobotRunProfileStateRobotDAPStarter extends CommandLineState {

    public RobotRunProfileStateRobotDAPStarter(@NotNull ExecutionEnvironment environment) {
        super(environment);
    }

    @NotNull
    private RobotRunProfileOptionsEditionAndPersistence getRunProfile() {
        RunProfile runProfile = getEnvironment().getRunProfile();
        if (!(runProfile instanceof RobotRunProfileOptionsEditionAndPersistence)) {
            throw new IllegalStateException("Got " + runProfile + " instead of RobotRunConfiguration profile");
        }
        return (RobotRunProfileOptionsEditionAndPersistence) runProfile;
    }

    @NotNull
    @Override
    protected ProcessHandler startProcess() throws ExecutionException {
        RobotRunProfileOptionsEditionAndPersistence runProfile = getRunProfile();
        GeneralCommandLine commandLine;
        // Note: the arguments are actually ignored at this point as we'll start the debug adapter
        // and not really the target process.
        commandLine = new GeneralCommandLine();
        RobotLaunchConfigRunOptions expandedOptions = runProfile.getOptions().getWithVarsExpanded(this.getEnvironment());

        // Validate if the target is correct.
        if (expandedOptions.target == null || expandedOptions.target.trim().isEmpty()) {
            throw new ExecutionException("Target not specified.");
        }

        Map<String, String> environment = commandLine.getEnvironment();
        environment.clear();
        if (expandedOptions.env != null) {
            environment.putAll(expandedOptions.env);
        }

        Project project = runProfile.getProject();
        LanguageServerDefinition languageServerDefinition;
        try {
            languageServerDefinition = RobotFrameworkLanguage.INSTANCE.getLanguageDefinition(project);
        } catch (CancelledException e) {
            throw new ExecutionException("Cancelled while getting language definition.");
        }
        if (languageServerDefinition == null) {
            throw new ExecutionException("Unable to find language server definition for project: " + project);
        }
        Object preferences;
        try {
            preferences = languageServerDefinition.getPreferences(project);
        } catch (CancelledException e) {
            throw new ExecutionException("Cancelled while getting preferences.");
        }
        if (!(preferences instanceof JsonObject)) {
            throw new ExecutionException("Expected preferences to be a JsonObject. Found: " + preferences);
        }
        JsonObject jsonObject = (JsonObject) preferences;
        JsonElement pythonExecutable = jsonObject.get(RobotPreferences.ROBOT_PYTHON_EXECUTABLE);
        if (pythonExecutable == null || pythonExecutable.getAsString().isEmpty()) {
            pythonExecutable = jsonObject.get(RobotPreferences.ROBOT_LANGUAGE_SERVER_PYTHON);
        }
        if (pythonExecutable == null || pythonExecutable.getAsString().isEmpty()) {
            String languageServerPython = RobotFrameworkLanguage.INSTANCE.getLanguageServerPython();
            if (languageServerPython != null) {
                pythonExecutable = new JsonPrimitive(languageServerPython);
            }
        }

        if (pythonExecutable == null || pythonExecutable.getAsString().isEmpty()) {
            throw new ExecutionException("The target python is not properly configured in the settings for making a launch.");
        }

        String python = pythonExecutable.getAsString();
        commandLine.setExePath(python);

        ParametersList parametersList = commandLine.getParametersList();

        // Note: we only start the debug adapter process at this point (launching the target
        // process will take place later).
        File dapMainScript = RobotFrameworkLanguage.INSTANCE.getDAPMainScript();
        // In debug mode it's all passed to the debug adapter at the launch message.
        parametersList.clearAll();
        parametersList.add("-u");
        parametersList.add(dapMainScript.getAbsolutePath());

        String workingDir = expandedOptions.computeWorkingDir();
        if (workingDir != null) {
            commandLine.setWorkDirectory(workingDir);
        } else {
            File targetRobot = new File(expandedOptions.target);
            if (targetRobot.isDirectory()) {
                commandLine.setWorkDirectory(targetRobot);
            } else {
                commandLine.setWorkDirectory(targetRobot.getParentFile());
            }
        }

        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        ByteArrayInputStream inputStream = new ByteArrayInputStream(new byte[0]);
        ProcessWrapper process = new ProcessWrapper(commandLine.createProcess()) {
            // i.e.: Don't provide the original streams as we have to use that for DAP communication.
            @Override
            public OutputStream getOutputStream() {
                return outputStream;
            }

            @Override
            public InputStream getInputStream() {
                return inputStream;
            }
        };

        String commandLineString = commandLine.getCommandLineString();
        Charset charset = commandLine.getCharset();
        KillableColoredProcessHandler processHandler = new RobotProcessHandler(process, commandLineString, charset, expandedOptions);
        processHandler.setHasPty(true);
        return processHandler;
    }

    @Nullable
    public static ConsoleView getConsoleView(ExecutionEnvironment executionEnv, ProcessHandler processHandler) {
        RunContentDescriptor contentDescriptor = RunContentManager.getInstance(executionEnv.getProject())
                .findContentDescriptor(executionEnv.getExecutor(), processHandler);

        ConsoleView console = null;
        if (contentDescriptor != null && contentDescriptor.getExecutionConsole() instanceof ConsoleView) {
            console = (ConsoleView) contentDescriptor.getExecutionConsole();
        }
        return console;
    }

    public class RobotProcessHandler extends KillableColoredProcessHandler {

        public final RobotLaunchConfigRunOptions expandedOptions;

        public RobotProcessHandler(Process process, String commandLineString, Charset charset, RobotLaunchConfigRunOptions expandedOptions) {
            super(process, commandLineString, charset);
            this.expandedOptions = expandedOptions;
        }

        @Override
        protected void notifyProcessTerminated(int exitCode) {
            ApplicationManager.getApplication().invokeLater(
                    () -> {
                        print("\n", ConsoleViewContentType.SYSTEM_OUTPUT);
                        print("Robot Run Terminated (code: " + exitCode + ")", ConsoleViewContentType.SYSTEM_OUTPUT);
                    }
            );
            super.notifyProcessTerminated(exitCode);
        }

        private void print(@NotNull String message, @NotNull ConsoleViewContentType consoleViewContentType) {
            ConsoleView console = getConsoleView(getEnvironment(), this);
            if (console != null) {
                console.print(message, consoleViewContentType);
            }
        }

        /**
         * Used to get the actual streams (to communicate to the debug adapter) -- by default the one
         * given is a wrapper which doesn't have a proper stdout/stdin (as those must
         * be used to communicate with the debug adapter).
         */
        public Process getDebugAdapterProcess() {
            ProcessWrapper process = (ProcessWrapper) getProcess();
            return process.getOriginalProcess();
        }
    }
}