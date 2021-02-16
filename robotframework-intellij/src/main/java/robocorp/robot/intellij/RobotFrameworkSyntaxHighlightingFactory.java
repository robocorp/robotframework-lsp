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

    @Override
    public @NotNull SyntaxHighlighter getSyntaxHighlighter(@Nullable Project project, @Nullable VirtualFile virtualFile) {
        return new Highlighter();
    }
}
