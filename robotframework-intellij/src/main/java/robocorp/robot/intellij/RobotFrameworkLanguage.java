package robocorp.robot.intellij;

import com.intellij.lang.Language;
import robocorp.lsp.intellij.ILSPLanguage;
import robocorp.lsp.intellij.LanguageServerDefinition;

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
        String robotLanguageServerPython = robotPreferences.getRobotLanguageServerPython();
        String robotLanguageServerArgs = robotPreferences.getRobotLanguageServerArgs();
        String robotLanguageServerTcpPort = robotPreferences.getRobotLanguageServerTcpPort().trim();
        int port = 0;
        if (!robotLanguageServerTcpPort.isEmpty()) {
            try {
                port = Integer.parseInt(robotLanguageServerTcpPort);
            } catch (NumberFormatException e) {
                // ignore
            }
        }

        // TODO: Don't hard-code this!
        String target = "X:/vscode-robot/robotframework-lsp/robotframework-ls/src/robotframework_ls/__main__.py";
        String python = "c:/bin/Miniconda/envs/py37_tests/python.exe";
        List<String> commands = Arrays.asList(python, "-u", target, "-vv", "--log-file=c:/temp/robotframework_ls.log");

        ProcessBuilder builder = new ProcessBuilder(commands);
        builder.redirectError(ProcessBuilder.Redirect.PIPE);
        builder.redirectOutput(ProcessBuilder.Redirect.PIPE);
        builder.redirectInput(ProcessBuilder.Redirect.PIPE);

        robotDefinition = new LanguageServerDefinition(
                new HashSet<>(Arrays.asList(".robot", ".resource")),
                builder,
                port,
                "RobotFramework"
        );

        robotPreferences.addListener((property, oldValue, newValue) -> {
            if (RobotPreferences.ROBOT_LANGUAGE_SERVER_PYTHON.equals(property) ||
                    RobotPreferences.ROBOT_LANGUAGE_SERVER_ARGS.equals(property) ||
                    RobotPreferences.ROBOT_LANGUAGE_SERVER_TCP_PORT.equals(property)) {
                // We must restart the language server!
            }
        });
    }

    public LanguageServerDefinition getLanguageDefinition() {
        return robotDefinition;
    }

}