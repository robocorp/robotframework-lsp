package robocorp.lsp.intellij;

import com.intellij.openapi.project.Project;

public interface ILanguageDefinitionContributor {
    LanguageServerDefinition getLanguageDefinition(Project project);
}
