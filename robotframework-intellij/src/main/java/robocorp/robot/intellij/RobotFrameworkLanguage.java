package robocorp.robot.intellij;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.intellij.lang.Language;
import com.intellij.notification.Notification;
import com.intellij.notification.NotificationType;
import com.intellij.notification.Notifications;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.ui.popup.JBPopupFactory;
import com.intellij.openapi.util.SystemInfo;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.ILSPLanguage;
import robocorp.lsp.intellij.LanguageServerDefinition;
import robocorp.lsp.intellij.SearchPython;

import java.io.File;
import java.net.URL;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;

/**
 * Interesting:
 * https://jetbrains.org/intellij/sdk/docs/tutorials/custom_language_support_tutorial.html
 * https://github.com/ballerina-platform/lsp4intellij
 */
public class RobotFrameworkLanguage extends Language implements ILSPLanguage {

    private static final Logger LOG = Logger.getInstance(RobotFrameworkLanguage.class);

    public static final RobotFrameworkLanguage INSTANCE = new RobotFrameworkLanguage();
    private final LanguageServerDefinition robotDefinition;
    private String robotFrameworkLSUserHome;

    public void setRobotFrameworkLSUserHome(String robotFrameworkLSUserHome) {
        this.robotFrameworkLSUserHome = robotFrameworkLSUserHome;
        // reset the current process builder when it changes
        robotDefinition.setProcessBuilder(createProcessBuilderFromPreferences());
    }

    private RobotFrameworkLanguage() {
        super("RobotFramework");

        // Note: for the real-world use-case packing the language server see:
        // https://intellij-support.jetbrains.com/hc/en-us/community/posts/206917225-Plugin-installation-as-unpacked-folder
        // Use to get proper path?
        // System.out.println(LanguageServerManagerTest.class.getResource("LanguageServerManagerTest.class"));

        // Note: the RobotPreferences are required to startup (so, we need a running intellij app environment
        // to startup -- this means that all tests must also be a subclass of LSPTestCase/BasePlatformTestCase).
        @Nullable RobotPreferences robotPreferences = RobotPreferences.getInstance();

        ProcessBuilder builder = createProcessBuilderFromPreferences();

        robotDefinition = new LanguageServerDefinition(
                new HashSet<>(Arrays.asList(".robot", ".resource")),
                builder,
                getPortFromPreferences(),
                "RobotFramework"
        ) {

            @Override
            public Object getPreferences() {
                @Nullable RobotPreferences robotPreferences = RobotPreferences.getInstance();
                if (robotPreferences == null) {
                    return new JsonObject();
                }
                return robotPreferences.asJsonObject();
            }

            @Override
            public void registerPreferencesListener(IPreferencesListener preferencesListener) {
                @Nullable RobotPreferences robotPreferences = RobotPreferences.getInstance();
                if (robotPreferences == null) {
                    return;
                }
                robotPreferences.addListener(preferencesListener);
            }

            @Override
            public void unregisterPreferencesListener(IPreferencesListener preferencesListener) {
                @Nullable RobotPreferences robotPreferences = RobotPreferences.getInstance();
                if (robotPreferences == null) {
                    return;
                }
                robotPreferences.removeListener(preferencesListener);
            }
        };

        if (robotPreferences != null) {
            robotPreferences.addListener((property, oldValue, newValue) -> {
                if (RobotPreferences.ROBOT_LANGUAGE_SERVER_PYTHON.equals(property) ||
                        RobotPreferences.ROBOT_LANGUAGE_SERVER_ARGS.equals(property)
                ) {
                    robotDefinition.setProcessBuilder(createProcessBuilderFromPreferences());
                } else if (RobotPreferences.ROBOT_LANGUAGE_SERVER_TCP_PORT.equals(property)) {
                    robotDefinition.setPort(getPortFromPreferences());
                }
            });
        }
    }

    private int getPortFromPreferences() {
        RobotPreferences robotPreferences = RobotPreferences.getInstance();
        if (robotPreferences == null) {
            return 0;
        }
        String robotLanguageServerTcpPort = robotPreferences.getRobotLanguageServerTcpPort().trim();
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
    private ProcessBuilder createProcessBuilderFromPreferences() {
        File main = getMain();

        @Nullable RobotPreferences robotPreferences = RobotPreferences.getInstance();
        @Nullable String python = SearchPython.getDefaultPythonExecutable();
        // python = "C:\\bin\\Miniconda\\envs\\py_38_tests\\python.exe";

        String robotLanguageServerPython = robotPreferences != null ? robotPreferences.getRobotLanguageServerPython().trim() : "";
        if (!robotLanguageServerPython.isEmpty()) {
            python = robotLanguageServerPython;
        }
        if (python == null) {
            // If we can't discover the python executable, we have to wait for the user to provide it.
            String msg = "Unable to find a python executable in the PATH.\n\nPlease configure the 'Language Server Python' in the 'Robot Framework Language Server' settings.";
            Notifications.Bus.notify(new Notification(
                    "Robot Framework Language Server", "Unable to start Robot Framework Language Server", msg, NotificationType.ERROR));
            LOG.error(msg);
            return null;
        }

        List<String> commands = new ArrayList(Arrays.asList(python, "-u", main.toString()));
        @Nullable JsonArray robotLanguageServerArgs = robotPreferences != null ? robotPreferences.getRobotLanguageServerArgsAsJson() : new JsonArray();
        if (robotLanguageServerArgs != null) {
            for (JsonElement e : robotLanguageServerArgs) {
                commands.add(e.toString());
            }
        }
        //else {
        //     commands.add("-vv");
        //     commands.add("--log-file=c:/temp/robotframework_ls.log");
        // }

        ProcessBuilder builder = new ProcessBuilder(commands);
        builder.redirectError(ProcessBuilder.Redirect.PIPE);
        builder.redirectOutput(ProcessBuilder.Redirect.PIPE);
        builder.redirectInput(ProcessBuilder.Redirect.PIPE);

        if (this.robotFrameworkLSUserHome != null) {
            builder.environment().put("ROBOTFRAMEWORK_LS_USER_HOME", this.robotFrameworkLSUserHome);
        }
        return builder;
    }

    /**
     * Finds out the __main__.py file location.
     */
    @NotNull
    private File getMain() {
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
            File main = new File(new File(pySrc, "robotframework_ls"), "__main__.py");
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
            File main = new File(new File(directory, "robotframework_ls"), "__main__.py");
            if (main.exists()) {
                return main;
            }
            builder.append("Target location:\n" + main + "\n");

            main = new File(new File(new File(new File(directory, "robotframework-ls"), "src"), "robotframework_ls"), "__main__.py");
            if (main.exists()) {
                return main;
            }
            builder.append("Target location:\n" + main + "\n");
            directory = directory.getParentFile();
        }
        throw new RuntimeException("Unable to discover __main__.py location.\nResource file: " + mainStr + "\nDetails:\n" + builder.toString());
    }

    public LanguageServerDefinition getLanguageDefinition() {
        return robotDefinition;
    }

}