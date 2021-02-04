package robocorp.robot.intellij;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.intellij.lang.Language;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.ILSPLanguage;
import robocorp.lsp.intellij.LanguageServerDefinition;

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

    public static final RobotFrameworkLanguage INSTANCE = new RobotFrameworkLanguage();
    private final LanguageServerDefinition robotDefinition;

    private RobotFrameworkLanguage() {
        super("RobotFramework");

        // Note: for the real-world use-case packing the language server see:
        // https://intellij-support.jetbrains.com/hc/en-us/community/posts/206917225-Plugin-installation-as-unpacked-folder
        // Use to get proper path?
        // System.out.println(LanguageServerManagerTest.class.getResource("LanguageServerManagerTest.class"));

        RobotPreferences robotPreferences = RobotPreferences.getInstance();

        ProcessBuilder builder = createProcessBuilderFromPreferences();

        robotDefinition = new LanguageServerDefinition(
                new HashSet<>(Arrays.asList(".robot", ".resource")),
                builder,
                getPortFromPreferences(),
                "RobotFramework"
        ) {

            @Override
            public Object getPreferences() {
                return RobotPreferences.getInstance().asJsonObject();
            }

            @Override
            public void registerPreferencesListener(IPreferencesListener preferencesListener) {
                RobotPreferences.getInstance().addListener(preferencesListener);
            }

            @Override
            public void unregisterPreferencesListener(IPreferencesListener preferencesListener) {
                RobotPreferences.getInstance().removeListener(preferencesListener);
            }
        };

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

    private int getPortFromPreferences() {
        RobotPreferences robotPreferences = RobotPreferences.getInstance();
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
        // TODO: Don't hard-code this!

        final String target = "X:/vscode-robot/robotframework-lsp/robotframework-ls/src/robotframework_ls/__main__.py";
        RobotPreferences robotPreferences = RobotPreferences.getInstance();
        String python = "python"; // i.e.: if it's in the PATH it should be picked up!
        String robotLanguageServerPython = robotPreferences.getRobotLanguageServerPython().trim();
        if (!robotLanguageServerPython.isEmpty()) {
            python = robotLanguageServerPython;
        }

        List<String> commands = new ArrayList(Arrays.asList(python, "-u", target));
        @Nullable JsonArray robotLanguageServerArgs = robotPreferences.getRobotLanguageServerArgsAsJson();
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

    public LanguageServerDefinition getLanguageDefinition() {
        return robotDefinition;
    }

}