package robocorp.lsp.intellij;

import com.intellij.openapi.project.Project;

public interface ILSPLanguage {
    LanguageServerDefinition getLanguageDefinition(Project project);
}
