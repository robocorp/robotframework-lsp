package robocorp.lsp.intellij.client;

import org.junit.Test;
import robocorp.lsp.intellij.client.startup.LanguageServerDefinition;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;

public class LanguageServerManagerTest {

    @Test
    public void testLanguageServerManager() throws Exception {

        // Note: for the real-world use-case packing the language server see:
        // https://intellij-support.jetbrains.com/hc/en-us/community/posts/206917225-Plugin-installation-as-unpacked-folder
        // Use to get proper path?
        // System.out.println(LanguageServerManagerTest.class.getResource("LanguageServerManagerTest.class"));

        LanguageServerDefinition robotDefinition;
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
                builder
        );

        LanguageServerManager languageServerManager = new LanguageServerManager(robotDefinition);

        // TODO: Don't hardcode this.
        String projectRoot = "X:\\vscode-robot\\robotframework-lsp\\robotframework-idea\\src\\test\\resources";
        try {
            languageServerManager.start(".robot", projectRoot);
        } finally {
            languageServerManager.stop(projectRoot);
        }

    }
}
