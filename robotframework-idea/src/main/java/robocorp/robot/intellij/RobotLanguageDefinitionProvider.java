package robocorp.robot.intellij;

import robocorp.lsp.intellij.ILanguageDefinitionContributor;
import robocorp.lsp.intellij.LanguageServerDefinition;

public class RobotLanguageDefinitionProvider implements ILanguageDefinitionContributor {
    @Override
    public LanguageServerDefinition getLanguageDefinition() {
        return RobotFrameworkLanguage.INSTANCE.getLanguageDefinition();
    }
}
