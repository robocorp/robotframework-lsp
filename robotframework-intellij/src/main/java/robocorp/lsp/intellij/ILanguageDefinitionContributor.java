package robocorp.lsp.intellij;

import com.intellij.openapi.project.Project;
import robocorp.robot.intellij.CancelledException;

public interface ILanguageDefinitionContributor {
    LanguageServerDefinition getLanguageDefinition(Project project) throws CancelledException;
}
