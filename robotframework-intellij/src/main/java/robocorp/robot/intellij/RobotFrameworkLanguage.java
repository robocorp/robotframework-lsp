package robocorp.robot.intellij;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.intellij.lang.Language;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.DialogBuilder;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.util.SystemInfo;
import com.intellij.ui.components.JBLabel;
import com.intellij.ui.components.JBTextArea;
import com.intellij.ui.components.JBTextField;
import com.intellij.util.ui.FormBuilder;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.*;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.awt.event.KeyListener;
import java.io.File;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Interesting:
 * https://jetbrains.org/intellij/sdk/docs/tutorials/custom_language_support_tutorial.html
 * https://github.com/ballerina-platform/lsp4intellij
 */
public class RobotFrameworkLanguage extends Language implements ILSPLanguage {

    private static final Logger LOG = Logger.getInstance(RobotFrameworkLanguage.class);

    public static final RobotFrameworkLanguage INSTANCE = new RobotFrameworkLanguage();
    private final Map<Project, LanguageServerDefinition> projectToDefinition = new HashMap<>();
    private final Object projectToDefinitionLock = new Object();
    private String robotFrameworkLSUserHome;
    private volatile boolean showingDialogToConfigureExecutable;
    private String languageServerPython;

    @Override
    public String getLanguageServerPython() {
        return languageServerPython;
    }

    public void setRobotFrameworkLSUserHome(String robotFrameworkLSUserHome) {
        this.robotFrameworkLSUserHome = robotFrameworkLSUserHome;
        // reset the current process builder when it changes
        synchronized (projectToDefinitionLock) {
            Set<Map.Entry<Project, LanguageServerDefinition>> entries = projectToDefinition.entrySet();
            for (Map.Entry<Project, LanguageServerDefinition> entry : entries) {
                entry.getValue().setProcessBuilder(createProcessBuilderFromPreferences(entry.getKey()));
            }
        }
    }

    private RobotFrameworkLanguage() {
        super("RobotFramework");
    }

    private int getPortFromPreferences(Project project) {
        RobotProjectPreferences projectPreferences = RobotProjectPreferences.getInstance(project);
        if (projectPreferences != null) {
            String tcpPort = projectPreferences.getRobotLanguageServerTcpPort();
            if (!tcpPort.isEmpty()) {
                try {
                    return Integer.parseInt(tcpPort);
                } catch (NumberFormatException e) {
                    // ignore
                }
            }
        }

        RobotPreferences appPreferences = RobotPreferences.getInstance();
        if (appPreferences == null) {
            return 0;
        }
        String robotLanguageServerTcpPort = appPreferences.getRobotLanguageServerTcpPort().trim();
        int port = 0;
        if (!robotLanguageServerTcpPort.isEmpty()) {
            try {
                port = Integer.parseInt(robotLanguageServerTcpPort);
            } catch (NumberFormatException e) {
                // ignore
            }
        }
        return port;
    }

    @Nullable
    private ProcessBuilder createProcessBuilderFromPreferences(Project project) {
        File main = getLSPMainScript();

        RobotProjectPreferences projectPreferences = RobotProjectPreferences.getInstance(project);

        @Nullable RobotPreferences robotAppPreferences = RobotPreferences.getInstance();

        // ---------------- Get Python executable

        @Nullable String python = SearchPython.getDefaultPythonExecutable();
        boolean foundPythonInPreferences = false;
        boolean foundValidPythonInPreferences = false;

        boolean develop = false;
        if (develop) {
            python = "C:\\bin\\Miniconda\\envs\\py_38_tests\\python.exe";
        }

        String robotLanguageServerPython = projectPreferences != null ? projectPreferences.getRobotLanguageServerPython().trim() : "";
        if (!robotLanguageServerPython.isEmpty()) {
            robotLanguageServerPython = replaceVariables(project, robotLanguageServerPython);
            foundPythonInPreferences = true;
            String msg;
            if ((msg = isValidPython(robotLanguageServerPython)) == null) {
                python = robotLanguageServerPython;
                foundValidPythonInPreferences = true;
            } else {
                // Notifications.Bus.notify(new Notification(
                //        "Robot Framework Language Server", "Invalid Python in Project preferences", msg, NotificationType.ERROR));
            }
        }

        if (!foundValidPythonInPreferences) {
            robotLanguageServerPython = robotAppPreferences != null ? robotAppPreferences.getRobotLanguageServerPython().trim() : "";
            if (!robotLanguageServerPython.isEmpty()) {
                robotLanguageServerPython = replaceVariables(project, robotLanguageServerPython);
                foundPythonInPreferences = true;
                String msg;
                if ((msg = isValidPython(robotLanguageServerPython)) == null) {
                    python = robotLanguageServerPython;
                    foundValidPythonInPreferences = true;
                } else {
                    // Notifications.Bus.notify(new Notification(
                    //        "Robot Framework Language Server", "Invalid Python in App preferences", msg, NotificationType.ERROR));
                }
            }
        }

        if (!foundPythonInPreferences) {
            // No Python in the preferences: use default
            String msg;
            if ((msg = isValidPython(python)) == null) {
                // Ok, go with default Python!
            } else {
                // If we can't discover the python executable, we have to wait for the user to provide it.
                // Notifications.Bus.notify(new Notification(
                //        "Robot Framework Language Server", "Unable to start Robot Framework Language Server", msg, NotificationType.ERROR));

                // Ask the user for a Python executable to actually start the language server.
                if (!showingDialogToConfigureExecutable) {
                    ApplicationManager.getApplication().invokeLater(() -> showDialogToConfigurePythonExecutable(project));
                }
                return null;
            }
        } else if (!foundValidPythonInPreferences) {
            // A Python in the preferences was found but wasn't valid: show UI to configure
            if (!showingDialogToConfigureExecutable) {
                ApplicationManager.getApplication().invokeLater(() -> showDialogToConfigurePythonExecutable(project));
            }
            return null;
        }

        this.languageServerPython = python;

        // ---------------- Get arguments

        List<String> commands = new ArrayList(Arrays.asList(python, "-u", main.toString()));

        @Nullable JsonArray robotLanguageServerArgs = projectPreferences != null ? projectPreferences.getRobotLanguageServerArgsAsJson() : new JsonArray();
        if (robotLanguageServerArgs == null) {
            robotLanguageServerArgs = robotAppPreferences != null ? robotAppPreferences.getRobotLanguageServerArgsAsJson() : new JsonArray();
        }

        if (robotLanguageServerArgs != null) {
            for (JsonElement e : robotLanguageServerArgs) {
                commands.add(replaceVariables(project, e.getAsString()));
            }
        }

        if (develop) {
            commands.add("-vv");
            commands.add("--log-file=c:/temp/robotframework_ls.log");
        }

        ProcessBuilder builder = new ProcessBuilder(commands);
        builder.redirectError(ProcessBuilder.Redirect.PIPE);
        builder.redirectOutput(ProcessBuilder.Redirect.PIPE);
        builder.redirectInput(ProcessBuilder.Redirect.PIPE);

        Map<String, String> environment = builder.environment();
        if (this.robotFrameworkLSUserHome != null) {
            environment.put("ROBOTFRAMEWORK_LS_USER_HOME", this.robotFrameworkLSUserHome);
        }
        String pythonpath = environment.get("PYTHONPATH");
        if (pythonpath == null) {
            pythonpath = "";
        }
        // i.e.: Make sure that the language server available in the plugin is the one used.
        if (pythonpath.trim().isEmpty()) {
            pythonpath = main.getParentFile().getParentFile().getAbsolutePath();
        } else {
            pythonpath = main.getParentFile().getParentFile().getAbsolutePath() + File.pathSeparator + pythonpath;
        }
        environment.put("PYTHONPATH", pythonpath);
        return builder;
    }

    private static final Pattern VARIABLES_PATTERN = Pattern.compile("\\$\\{([^\\{\\}]*)\\}");

    private String replaceVariables(Project project, String robotLanguageServerPython) {
        Matcher matcher = VARIABLES_PATTERN.matcher(robotLanguageServerPython);
        return matcher.replaceAll((matchResult -> {
            String s = matchResult.group(1);
            String value = null;
            if (s.startsWith("env.") || s.startsWith("env:")) {
                value = System.getenv(s.substring(4));
            } else {
                if (s.equals("workspace") || s.equals("workspaceRoot") || s.equals("workspaceFolder")) {
                    value = project.getBasePath();
                }
            }
            if (value == null) {
                value = matchResult.group(0);
            }
            return value;
        }));
    }

    private JBTextArea createJTextArea(String text) {
        JBTextArea f = new JBTextArea();
        f.setText(text);
        f.setEditable(false);
        f.setBackground(null);
        f.setBorder(null);
        f.setFont(UIManager.getFont("Label.font"));
        return f;
    }

    private void showDialogToConfigurePythonExecutable(Project project) {
        if (EditorUtils.isHeadlessEnv()) {
            return;
        }
        if (showingDialogToConfigureExecutable) {
            return;
        }
        showingDialogToConfigureExecutable = true;
        try {
            final @Nullable RobotPreferences preferences = RobotPreferences.getInstance();
            final @Nullable RobotProjectPreferences projectPreferences = RobotProjectPreferences.getInstance(project);
            if (preferences == null) {
                LOG.error("Unable to get preferences.");
                return;
            }

            final JBTextField robotLanguageServerPython = new JBTextField();
            final JBTextField robotLanguageServerArgs = new JBTextField();

            // Set initial values.
            if (projectPreferences != null) {
                robotLanguageServerPython.setText(projectPreferences.getRobotLanguageServerPython());
            }
            if (robotLanguageServerPython.getText().trim().isEmpty()) {
                robotLanguageServerPython.setText(preferences.getRobotLanguageServerPython());
            }
            if (projectPreferences != null) {
                robotLanguageServerArgs.setText(projectPreferences.getRobotLanguageServerArgs());
            }
            if (robotLanguageServerArgs.getText().trim().isEmpty()) {
                robotLanguageServerArgs.setText(preferences.getRobotLanguageServerArgs());
            }

            final JBLabel errorLabel = new JBLabel("");
            errorLabel.setForeground(Color.RED);
            JBTextArea area1 = createJTextArea("Specifies the path to the python executable to be used for the Robot Framework Language Server (the\ndefault is searching python on the PATH).\n\n");
            JBTextArea area2 = createJTextArea("Specifies the arguments to be passed to the robotframework language server (i.e.: [\"-vv\", \"--log-file=~/robotframework_ls.log\"]).\nNote: expected format: JSON Array\n\n");
            KeyListener listener = new KeyAdapter() {
                @Override
                public void keyReleased(KeyEvent e) {
                    errorLabel.setText("");
                }
            };
            area1.addKeyListener(listener);
            final JPanel panel = FormBuilder.createFormBuilder()
                    .addComponent(createJTextArea("Please provide information on the Python executable and arguments to be able to start the Robot Framework Language Server.\n"))
                    .addLabeledComponent(new JBLabel("Language Server Python"), robotLanguageServerPython, 1, false)
                    .addComponent(area1)
                    .addLabeledComponent(new JBLabel("Language Server Args"), robotLanguageServerArgs, 1, false)
                    .addComponent(area2)
                    .addComponent(errorLabel)
                    .addComponentFillVertically(new JPanel(), 0)
                    .getPanel();

            DialogBuilder builder = new DialogBuilder();
            builder.setCenterPanel(panel);
            builder.setTitle("Robot Framework Language Server");
            builder.removeAllActions();
            final int SAVE_IN_APP = DialogWrapper.NEXT_USER_EXIT_CODE;
            final int SAVE_IN_PROJECT = DialogWrapper.NEXT_USER_EXIT_CODE + 1;

            Supplier<Boolean> validate = () -> {
                String errorMsg = preferences.validateRobotLanguageServerPython(robotLanguageServerPython.getText());
                if (!errorMsg.isEmpty()) {
                    errorLabel.setText(errorMsg);
                    return false;
                }
                errorMsg = preferences.validateRobotLanguageServerArgs(robotLanguageServerArgs.getText());
                if (!errorMsg.isEmpty()) {
                    errorLabel.setText(errorMsg);
                    return false;
                }
                String validPython = isValidPython(robotLanguageServerPython.getText());
                if (validPython != null) {
                    errorLabel.setText(validPython);
                    return false;
                }
                errorLabel.setText("");
                return true;
            };
            builder.addAction(new AbstractAction("Save in User settings") {
                @Override
                public void actionPerformed(ActionEvent e) {
                    if (!validate.get()) {
                        return;
                    }
                    builder.getDialogWrapper().close(SAVE_IN_APP);
                }
            });
            builder.addAction(new AbstractAction("Save in Project settings") {
                @Override
                public void actionPerformed(ActionEvent e) {
                    if (!validate.get()) {
                        return;
                    }
                    builder.getDialogWrapper().close(SAVE_IN_PROJECT);
                }
            });
            builder.addCancelAction();
            validate.get(); // Validate once with initial values prior to starting.

            int code = builder.show();
            switch (code) {
                case SAVE_IN_APP:
                    preferences.setRobotLanguageServerPython(robotLanguageServerPython.getText());
                    preferences.setRobotLanguageServerArgs(robotLanguageServerArgs.getText());
                    break;
                case SAVE_IN_PROJECT:
                    projectPreferences.setRobotLanguageServerPython(robotLanguageServerPython.getText());
                    projectPreferences.setRobotLanguageServerArgs(robotLanguageServerArgs.getText());
                    break;
            }

        } finally {
            showingDialogToConfigureExecutable = false;
        }
    }

    private String isValidPython(String robotLanguageServerPython) {
        if (robotLanguageServerPython == null || robotLanguageServerPython.length() == 0) {
            return "Python executable not specified.";
        }
        if (!new File(robotLanguageServerPython).exists()) {
            return robotLanguageServerPython + " does not exist.";
        }

        ProcessBuilder builder = new ProcessBuilder(robotLanguageServerPython, "-c", "import sys;sys.stderr.write('%s.%s\\n' % sys.version_info[:2]);");
        builder.redirectError(ProcessBuilder.Redirect.PIPE);
        builder.redirectOutput(ProcessBuilder.Redirect.PIPE);
        builder.redirectInput(ProcessBuilder.Redirect.PIPE);
        try {
            Process process = builder.start();
            InputStream errorStream = process.getErrorStream();
            process.waitFor(2, TimeUnit.SECONDS);
            byte[] b = errorStream.readAllBytes();
            String s = new String(b, StandardCharsets.UTF_8);
            List<String> split = StringUtils.split(s.trim(), '.');
            int majorVersion = Integer.parseInt(split.get(0));
            if (majorVersion <= 2) {
                return "Python executable specified has version: " + s + " (Python 3 onwards is required).";
            }

        } catch (Exception e) {
            return "Unable to execute " + robotLanguageServerPython + " error: " + e.toString();
        }

        return null;
    }

    public File getLSPMainScript() {
        return getMainScript("robotframework_ls");
    }

    public File getDAPMainScript() {
        return getMainScript("robotframework_debug_adapter");
    }

    /**
     * Finds out the __main__.py file location.
     */
    @NotNull
    public static File getMainScript(final String packageName) {
        URL resourceURL = RobotFrameworkLanguage.class.getClassLoader().getResource("robotframework-intellij-resource.txt");
        File resourceFile = new File(resourceURL.getFile());
        StringBuilder builder = new StringBuilder();

        if (resourceFile.exists()) {
            // In dev it's something as:
            // ...robotframework-lsp/robotframework-intellij/src/main/resources/robotframework-intellij-resource.txt
            // and we want:
            // ...robotframework-lsp/robotframework-ls/__main__.py
            File parentFile = resourceFile.getParentFile().getParentFile().getParentFile().getParentFile().getParentFile();
            File pySrc = new File(new File(parentFile, "robotframework-ls"), "src");
            File main = new File(new File(pySrc, packageName), "__main__.py");
            if (main.exists()) {
                return main;
            }
            builder.append("Target location:\n" + main + "\n");
        }

        String mainStr = resourceFile.toString();
        if (mainStr.startsWith("file:/") || mainStr.startsWith("file:\\")) {
            mainStr = mainStr.substring(6);
            if (!SystemInfo.isWindows) {
                if (!mainStr.startsWith("/")) {
                    mainStr = "/" + mainStr;
                }
            }
        }

        File directory;
        if (mainStr.contains("jar!")) {
            // Something as:
            // file:\D:\x\vscode-robot\robotframework-lsp\robotframework-intellij\build\idea-sandbox\plugins\robotframework-intellij\lib\robotframework-intellij-0.7.1.jar!\robotframework-intellij-resource.txt
            // Search in the lib dir (along the .jar).
            int i = mainStr.lastIndexOf("jar!");
            String substring = mainStr.substring(0, i);
            directory = new File(substring);
        } else {
            directory = new File(mainStr);
        }

        while (directory != null) {
            File main = checkDirectoryForMain(packageName, builder, directory);
            if (main != null) {
                return main;
            }

            // Let's see if it's url-quoted.
            try {
                String dirAsAbsolute = directory.getAbsolutePath();
                String decoded = java.net.URLDecoder.decode(dirAsAbsolute, StandardCharsets.UTF_8.name());
                if (decoded != null && !decoded.equals(dirAsAbsolute)) {
                    main = checkDirectoryForMain(packageName, builder, new File(decoded));
                    if (main != null) {
                        return main;
                    }
                }
            } catch (Exception e) {
                LOG.error(e);
            }

            directory = directory.getParentFile();
        }
        throw new RuntimeException("Unable to discover __main__.py location.\nResource file: " + mainStr + "\nDetails:\n" + builder.toString());
    }

    @Nullable
    private static File checkDirectoryForMain(final String packageName, StringBuilder builder, File directory) {
        if (!directory.exists()) {
            builder.append("Directory: " + directory + " does not exist.\n");
            return null;
        }
        File main = new File(new File(directory, packageName), "__main__.py");
        if (main.exists()) {
            return main;
        }
        builder.append("Checked" + main + "\n");

        main = new File(new File(new File(new File(directory, "robotframework-ls"), "src"), packageName), "__main__.py");
        if (main.exists()) {
            return main;
        }
        builder.append("Checked:" + main + "\n");
        return null;
    }

    public LanguageServerDefinition getLanguageDefinition(final Project project) {
        synchronized (projectToDefinitionLock) {
            LanguageServerDefinition definition = projectToDefinition.get(project);
            if (definition == null) {
                definition = createLanguageServerDefinition(project);
                projectToDefinition.put(project, definition);
            }
            return definition;
        }
    }

    private LanguageServerDefinition createLanguageServerDefinition(final Project project) {
        // Note: for the real-world use-case packing the language server see:
        // https://intellij-support.jetbrains.com/hc/en-us/community/posts/206917225-Plugin-installation-as-unpacked-folder
        // Use to get proper path?
        // System.out.println(LanguageServerManagerTest.class.getResource("LanguageServerManagerTest.class"));

        final LanguageServerDefinition definition = new LanguageServerDefinition(
                new HashSet<>(Arrays.asList(".robot", ".resource")),
                createProcessBuilderFromPreferences(project),
                getPortFromPreferences(project),
                "RobotFramework"
        ) {

            @Override
            public Object getPreferences(Project project) {
                // Get the basic app preferences.
                @Nullable RobotPreferences robotAppPreferences = RobotPreferences.getInstance();
                JsonObject jsonObject;
                if (robotAppPreferences == null) {
                    jsonObject = new JsonObject();
                } else {
                    jsonObject = robotAppPreferences.asJsonObject();
                }

                // Override project-specific preferences.
                RobotProjectPreferences robotProjectPreferences = RobotProjectPreferences.getInstance(project);
                if (robotProjectPreferences != null) {
                    JsonObject projectJsonObject = robotProjectPreferences.asJsonObject();
                    Set<Map.Entry<String, JsonElement>> entries = projectJsonObject.entrySet();
                    for (Map.Entry<String, JsonElement> entry : entries) {
                        jsonObject.add(entry.getKey(), entry.getValue());
                    }
                }
                return jsonObject;
            }

            @Override
            public void registerPreferencesListener(Project project, IPreferencesListener preferencesListener) {
                @Nullable RobotPreferences robotAppPreferences = RobotPreferences.getInstance();
                if (robotAppPreferences != null) {
                    robotAppPreferences.addListener(preferencesListener);
                }
                RobotProjectPreferences robotProjectPreferences = RobotProjectPreferences.getInstance(project);
                if (robotProjectPreferences != null) {
                    robotProjectPreferences.addListener(preferencesListener);
                }
            }

            @Override
            public void unregisterPreferencesListener(Project project, IPreferencesListener preferencesListener) {
                @Nullable RobotPreferences robotAppPreferences = RobotPreferences.getInstance();
                if (robotAppPreferences != null) {
                    robotAppPreferences.removeListener(preferencesListener);
                }
                RobotProjectPreferences robotProjectPreferences = RobotProjectPreferences.getInstance(project);
                if (robotProjectPreferences != null) {
                    robotProjectPreferences.removeListener(preferencesListener);
                }
            }
        };

        LanguageServerDefinition.IPreferencesListener listener = (property, oldValue, newValue) -> {
            if (RobotPreferences.ROBOT_LANGUAGE_SERVER_PYTHON.equals(property) ||
                    RobotPreferences.ROBOT_LANGUAGE_SERVER_ARGS.equals(property)
            ) {
                definition.setProcessBuilder(createProcessBuilderFromPreferences(project));
            } else if (RobotPreferences.ROBOT_LANGUAGE_SERVER_TCP_PORT.equals(property)) {
                definition.setPort(getPortFromPreferences(project));
            }
        };

        // Note: the RobotPreferences are required to startup (so, we need a running intellij app environment
        // to startup -- this means that all tests must also be a subclass of LSPTestCase/BasePlatformTestCase).
        @Nullable RobotPreferences robotAppPreferences = RobotPreferences.getInstance();

        if (robotAppPreferences != null) {
            robotAppPreferences.addListener(listener);
        }

        RobotProjectPreferences projectPreferences = RobotProjectPreferences.getInstance(project);
        if (projectPreferences != null) {
            projectPreferences.addListener(listener);
        }
        return definition;
    }

}