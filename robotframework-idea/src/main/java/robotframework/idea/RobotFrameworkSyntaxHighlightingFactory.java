package robotframework.idea;

import com.intellij.lexer.Lexer;
import com.intellij.lexer.LexerBase;
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors;
import com.intellij.openapi.editor.colors.TextAttributesKey;
import com.intellij.openapi.fileTypes.SyntaxHighlighter;
import com.intellij.openapi.fileTypes.SyntaxHighlighterFactory;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.tree.IElementType;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

class RobotLexer extends LexerBase {

    private CharSequence buffer;
    private int startOffset;
    private int endOffset;
    private int initialState;

    private int position;
    private int tokenStartPosition;
    private IElementType currentToken;

    @Override
    public void start(@NotNull CharSequence buffer, int startOffset, int endOffset, int initialState) {
        this.buffer = buffer;
        this.startOffset = startOffset;
        this.endOffset = endOffset;
        this.initialState = initialState;

        this.tokenStartPosition = startOffset;
        this.position = startOffset;
        advance();
    }

    @Override
    public int getState() {
        return 0;
    }

    @Override
    public @Nullable IElementType getTokenType() {
        return currentToken;
    }

    @Override
    public int getTokenStart() {
        return this.tokenStartPosition;
    }

    @Override
    public int getTokenEnd() {
        return this.position;
    }

    @Override
    public void advance() {
        this.tokenStartPosition = this.position;
        if (this.position >= this.getBufferEnd()) {
            this.currentToken = null;
            return;
        }
        this.currentToken = RobotElementType.DEFAULT;

        char c = this.buffer.charAt(this.position);
        if (c == '\r' || c == '\n') {
            this.currentToken = RobotElementType.HEADING;
            skipNewLines();
            return;
        }
        if (c == '*') {
            if (isHeading(this.position)) {
                this.currentToken = RobotElementType.HEADING;
                goToEndOfLine();
                return;
            }
        }

        goToEndOfLine();
    }

    private boolean isHeading(int position) {
        return charAtEquals(position, '*') &&
                charAtEquals(position + 1, '*') &&
                charAtEquals(position + 2, '*') &&
                isSpace(position + 3);
    }

    private boolean isSpace(int position) {
        return charAtEquals(position, ' ');
    }

    private boolean charAtEquals(int position, char c) {
        return position < this.getBufferEnd() && this.buffer.charAt(position) == c;
    }

    private boolean isNewLine(int position) {
        return charAtEquals(position, '\n') || charAtEquals(position, '\r');
    }

    private void skipNewLines() {
        while (isNewLine(this.position)) {
            this.position++;
        }
    }

    private void goToEndOfLine() {
        while (this.position < this.getBufferEnd() && !isNewLine(this.position)) {
            this.position++;
        }
    }

    @Override
    public @NotNull CharSequence getBufferSequence() {
        return buffer;
    }

    @Override
    public int getBufferEnd() {
        return Math.min(this.endOffset, buffer.length());
    }
}


class Highlighter implements @NotNull SyntaxHighlighter {
    @Override
    public @NotNull Lexer getHighlightingLexer() {
        return new RobotLexer();
    }

    @Override
    public TextAttributesKey @NotNull [] getTokenHighlights(IElementType tokenType) {
        if (tokenType == RobotElementType.HEADING) {
            return new TextAttributesKey[]{RobotFrameworkSyntaxHighlightingFactory.HEADING};
        }
        return new TextAttributesKey[0];
    }
}

public class RobotFrameworkSyntaxHighlightingFactory extends SyntaxHighlighterFactory {

    public static final TextAttributesKey HEADING = TextAttributesKey.createTextAttributesKey(RobotElementType.HEADING.toString(), DefaultLanguageHighlighterColors.STRING);

    @Override
    public @NotNull SyntaxHighlighter getSyntaxHighlighter(@Nullable Project project, @Nullable VirtualFile virtualFile) {
        return new Highlighter();
    }
}
