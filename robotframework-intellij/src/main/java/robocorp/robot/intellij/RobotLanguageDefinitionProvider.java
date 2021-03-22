package robocorp.robot.intellij;

import com.intellij.openapi.project.Project;
import robocorp.lsp.intellij.ILanguageDefinitionContributor;
import robocorp.lsp.intellij.LanguageServerDefinition;

public class RobotLanguageDefinitionProvider implements ILanguageDefinitionContributor {
    @Override
    public LanguageServerDefinition getLanguageDefinition(Project project) {
        return RobotFrameworkLanguage.INSTANCE.getLanguageDefinition(project);
    }
}
