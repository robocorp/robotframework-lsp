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

    private static int STATE_AFTER_NEW_LINE = 0;
    private static int STATE_DEFAULT = 1;
    private int state;

    @Override
    public void start(@NotNull CharSequence buffer, int startOffset, int endOffset, int initialState) {
        this.buffer = buffer;
        this.startOffset = startOffset;
        this.endOffset = endOffset;
        this.initialState = initialState;

        this.tokenStartPosition = startOffset;
        this.position = startOffset;
        this.state = initialState;
        advance();
    }

    @Override
    public int getState() {
        return state;
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
        int currState = state;

        char c = this.buffer.charAt(this.position);
        if (c == '\r' || c == '\n') {
            this.currentToken = RobotElementType.NEW_LINE;
            state = STATE_AFTER_NEW_LINE;
            skipNewLines();
            return;
        }
        if (c == ' ' || c == '\t') {
            this.currentToken = RobotElementType.WHITESPACE;
            skipWhitespaces();
            return;
        }
        state = STATE_DEFAULT;

        if (currState == STATE_AFTER_NEW_LINE) {
            if (c == '*' && isHeading(this.position)) {
                this.currentToken = RobotElementType.HEADING;
                goToEndOfLine();
            } else if (c == '#') {
                this.currentToken = RobotElementType.COMMENT;
                goToEndOfLine();
            }
        }
        goToSpaceOrEndOfLine();
    }

    private boolean isHeading(int position) {
        return charAtEquals(position, '*') &&
                charAtEquals(position + 1, '*') &&
                charAtEquals(position + 2, '*');
    }

    private boolean charAtEquals(int position, char c) {
        return position < this.getBufferEnd() && this.buffer.charAt(position) == c;
    }

    private boolean isNewLine(int position) {
        return charAtEquals(position, '\n') || charAtEquals(position, '\r');
    }

    private boolean isSpace(int position) {
        return charAtEquals(position, ' ') || charAtEquals(position, '\t');
    }

    private void skipNewLines() {
        while (isNewLine(this.position)) {
            this.position++;
        }
    }

    private void skipWhitespaces() {
        while (isSpace(this.position)) {
            this.position++;
        }
    }

    private void goToEndOfLine() {
        while (this.position < this.getBufferEnd() && !isNewLine(this.position)) {
            this.position++;
        }
    }

    private void goToSpaceOrEndOfLine() {
        while (this.position < this.getBufferEnd()) {
            char c = this.buffer.charAt(position);
            if (c != ' ' && c != '\t' && c != '\n' && c != '\r') {
                this.position++;
            } else {
                break;
            }
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
