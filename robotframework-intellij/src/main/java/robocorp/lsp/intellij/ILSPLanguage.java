package robocorp.lsp.intellij;

import com.intellij.openapi.project.Project;
import robocorp.robot.intellij.CancelledException;

import java.io.File;

public interface ILSPLanguage {
    LanguageServerDefinition getLanguageDefinition(Project project) throws CancelledException;

    File getLSPMainScript();

    File getDAPMainScript();

    String getLanguageServerPython();
}
