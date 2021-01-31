package robocorp.robot.intellij;

import com.intellij.lexer.LexerBase;
import com.intellij.psi.tree.IElementType;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public class RobotLexer extends LexerBase {

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
            this.currentToken = RobotElementType.WHITESPACE;
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
