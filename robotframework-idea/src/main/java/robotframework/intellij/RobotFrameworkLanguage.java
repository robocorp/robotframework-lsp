package robotframework.intellij;

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
                "RobotFramework"
        );
    }

    public LanguageServerDefinition getLanguageDefinition() {
        return robotDefinition;
    }

}