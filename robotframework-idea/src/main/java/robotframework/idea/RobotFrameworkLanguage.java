package robotframework.idea;

import com.intellij.lang.Language;

/**
 * Interesting:
 * https://jetbrains.org/intellij/sdk/docs/tutorials/custom_language_support_tutorial.html
 * https://github.com/ballerina-platform/lsp4intellij
 */
public class RobotFrameworkLanguage extends Language {

    public static final RobotFrameworkLanguage INSTANCE = new RobotFrameworkLanguage();

    private RobotFrameworkLanguage() {
        super("RobotFramework");
    }

}