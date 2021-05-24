package robocorp.robot.intellij;

import com.intellij.lexer.Lexer;
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors;
import com.intellij.openapi.editor.colors.TextAttributesKey;
import com.intellij.openapi.fileTypes.SyntaxHighlighter;
import com.intellij.openapi.fileTypes.SyntaxHighlighterFactory;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.tree.IElementType;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.HashMap;
import java.util.Map;

class Highlighter implements @NotNull SyntaxHighlighter {
    @Override
    public @NotNull Lexer getHighlightingLexer() {
        return new RobotLexer();
    }

    @Override
    public TextAttributesKey @NotNull [] getTokenHighlights(IElementType tokenType) {
        if (tokenType == RobotElementType.HEADING) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.HEADING};
        } else if (tokenType == RobotElementType.COMMENT) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.COMMENT};
        } else if (tokenType == RobotElementType.VARIABLE) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.VARIABLE};
        } else if (tokenType == RobotElementType.PARAMETER_NAME) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.PARAMETER_NAME};
        } else if (tokenType == RobotElementType.ARGUMENT_VALUE) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.ARGUMENT_VALUE};
        } else if (tokenType == RobotElementType.NAME) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.NAME};
        } else if (tokenType == RobotElementType.SETTING) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.SETTING};
        } else if (tokenType == RobotElementType.KEYWORD) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.KEYWORD};
        } else if (tokenType == RobotElementType.VARIABLE_OPERATOR) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.VARIABLE_OPERATOR};
        } else if (tokenType == RobotElementType.KEYWORD_CALL) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.KEYWORD_CALL};
        } else if (tokenType == RobotElementType.SETTING_OPERATOR) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.SETTING_OPERATOR};
        } else if (tokenType == RobotElementType.CONTROL) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.CONTROL};
        } else if (tokenType == RobotElementType.TEST_CASE_NAME) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.TEST_CASE_NAME};
        }
        return new TextAttributesKey[0];
    }
}

public class RobotFrameworkSyntaxHighlightingFactory extends SyntaxHighlighterFactory {

    public static final TextAttributesKey HEADING = TextAttributesKey.createTextAttributesKey(
            RobotElementType.HEADING.toString(), DefaultLanguageHighlighterColors.KEYWORD);

    public static final TextAttributesKey COMMENT = TextAttributesKey.createTextAttributesKey(
            RobotElementType.COMMENT.toString(), DefaultLanguageHighlighterColors.LINE_COMMENT);

    public static final TextAttributesKey VARIABLE = TextAttributesKey.createTextAttributesKey(
            RobotElementType.VARIABLE.toString(), DefaultLanguageHighlighterColors.INSTANCE_FIELD);

    public static final TextAttributesKey PARAMETER_NAME = TextAttributesKey.createTextAttributesKey(
            RobotElementType.PARAMETER_NAME.toString(), DefaultLanguageHighlighterColors.NUMBER);

    public static final TextAttributesKey ARGUMENT_VALUE = TextAttributesKey.createTextAttributesKey(
            RobotElementType.ARGUMENT_VALUE.toString(), DefaultLanguageHighlighterColors.PARAMETER);

    public static final TextAttributesKey NAME = TextAttributesKey.createTextAttributesKey(
            RobotElementType.NAME.toString(), DefaultLanguageHighlighterColors.STRING);

    public static final TextAttributesKey SETTING = TextAttributesKey.createTextAttributesKey(
            RobotElementType.SETTING.toString(), DefaultLanguageHighlighterColors.METADATA);

    public static final TextAttributesKey KEYWORD = TextAttributesKey.createTextAttributesKey(
            RobotElementType.KEYWORD.toString(), DefaultLanguageHighlighterColors.FUNCTION_DECLARATION);

    public static final TextAttributesKey VARIABLE_OPERATOR = TextAttributesKey.createTextAttributesKey(
            RobotElementType.VARIABLE_OPERATOR.toString(), DefaultLanguageHighlighterColors.PARENTHESES);

    public static final TextAttributesKey KEYWORD_CALL = TextAttributesKey.createTextAttributesKey(
            RobotElementType.KEYWORD_CALL.toString(), DefaultLanguageHighlighterColors.METADATA);

    public static final TextAttributesKey SETTING_OPERATOR = TextAttributesKey.createTextAttributesKey(
            RobotElementType.SETTING_OPERATOR.toString(), DefaultLanguageHighlighterColors.PARENTHESES);

    public static final TextAttributesKey CONTROL = TextAttributesKey.createTextAttributesKey(
            RobotElementType.CONTROL.toString(), DefaultLanguageHighlighterColors.KEYWORD);

    public static final TextAttributesKey TEST_CASE_NAME = TextAttributesKey.createTextAttributesKey(
            RobotElementType.TEST_CASE_NAME.toString(), DefaultLanguageHighlighterColors.FUNCTION_DECLARATION);

    private static Map<String, TextAttributesKey> lspTypeToTextAttributeKey = new HashMap<>();

    static {
        lspTypeToTextAttributeKey.put("header", HEADING);
        lspTypeToTextAttributeKey.put("comment", COMMENT);
        lspTypeToTextAttributeKey.put("variable", VARIABLE);
        lspTypeToTextAttributeKey.put("parameterName", PARAMETER_NAME);
        lspTypeToTextAttributeKey.put("argumentValue", ARGUMENT_VALUE);
        lspTypeToTextAttributeKey.put("name", NAME);
        lspTypeToTextAttributeKey.put("setting", SETTING);
        lspTypeToTextAttributeKey.put("keywordNameDefinition", KEYWORD);
        lspTypeToTextAttributeKey.put("variableOperator", VARIABLE_OPERATOR);
        lspTypeToTextAttributeKey.put("keywordNameCall", KEYWORD_CALL);
        lspTypeToTextAttributeKey.put("settingOperator", VARIABLE);
        lspTypeToTextAttributeKey.put("control", CONTROL);
        lspTypeToTextAttributeKey.put("testCaseName", TEST_CASE_NAME);
    }

    public static TextAttributesKey getFromType(String s) {
        return lspTypeToTextAttributeKey.get(s);
    }

    @Override
    public @NotNull SyntaxHighlighter getSyntaxHighlighter(@Nullable Project project, @Nullable VirtualFile virtualFile) {
        return new Highlighter();
    }
}
