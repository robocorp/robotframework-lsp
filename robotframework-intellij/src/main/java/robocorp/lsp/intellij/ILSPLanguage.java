package robocorp.lsp.intellij;

import com.intellij.openapi.project.Project;

import java.io.File;

public interface ILSPLanguage {
    LanguageServerDefinition getLanguageDefinition(Project project);

    File getLSPMainScript();

    File getDAPMainScript();

    String getLanguageServerPython();
}
