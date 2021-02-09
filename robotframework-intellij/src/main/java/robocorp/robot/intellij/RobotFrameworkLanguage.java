package robocorp.robot.intellij;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.intellij.lang.Language;
import com.intellij.openapi.diagnostic.Logger;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.ILSPLanguage;
import robocorp.lsp.intellij.LanguageServerDefinition;

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

    @NotNull
    private ProcessBuilder createProcessBuilderFromPreferences() {
        File main = getMain();

        @Nullable RobotPreferences robotPreferences = RobotPreferences.getInstance();
        String python = "python"; // i.e.: if it's in the PATH it should be picked up!

        String robotLanguageServerPython = robotPreferences != null ? robotPreferences.getRobotLanguageServerPython().trim() : "";
        if (!robotLanguageServerPython.isEmpty()) {
            python = robotLanguageServerPython;
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
            // robotframework-lsp/robotframework-intellij/src/main/resources/robotframework-intellij-resource.txt
            // and we want:
            // robotframework-lsp/robotframework-ls/__main__.py
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
        }

        if (mainStr.contains("jar!")) {
            // Something as:
            // file:\D:\x\vscode-robot\robotframework-lsp\robotframework-intellij\build\idea-sandbox\plugins\robotframework-intellij\lib\robotframework-intellij-0.7.1.jar!\robotframework-intellij-resource.txt
            // Search in the lib dir (along the .jar).
            int i = mainStr.lastIndexOf("jar!");
            String substring = mainStr.substring(0, i);
            File libDir = new File(substring).getParentFile();
            File main = new File(new File(libDir, "robotframework_ls"), "__main__.py");
            if (main.exists()) {
                return main;
            }
            builder.append("Target location:\n" + main + "\n");

            // Also check in the lib dir parent (inside of robotframework-intellij).
            main = new File(new File(libDir.getParentFile(), "robotframework_ls"), "__main__.py");
            if (main.exists()) {
                return main;
            }
            builder.append("Target location:\n" + main + "\n");
        }

        if (mainStr.contains("jar!") && mainStr.contains("idea-sandbox") && mainStr.contains("robotframework-lsp")) {
            // Still in dev mode when inside the idea-sandbox (on gradlew buildPlugin).
            // It's something as:
            // file:\D:\x\vscode-robot\robotframework-lsp\robotframework-intellij\build\idea-sandbox\plugins\robotframework-intellij\lib\robotframework-intellij-0.7.1.jar!\robotframework-intellij-resource.txt
            int i = mainStr.lastIndexOf("robotframework-lsp");
            String substring = mainStr.substring(0, i);
            File p1 = new File(substring, "robotframework-ls");
            if (p1.exists()) {
                File p2 = new File(p1, "src");
                if (p2.exists()) {
                    File main = new File(new File(p2, "robotframework_ls"), "__main__.py");
                    if (main.exists()) {
                        return main;
                    }
                } else {
                    builder.append("Target location:\n" + p2 + " does not exist\n");
                }
            } else {
                builder.append("Target location:\n" + p1 + " does not exist\n");
            }
        }

        throw new RuntimeException("Unable to discover __main__.py location.\nResource file: " + mainStr + "\nDetails:\n" + builder.toString());
    }

    public LanguageServerDefinition getLanguageDefinition() {
        return robotDefinition;
    }

}