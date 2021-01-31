package robotframework.intellij;

import com.intellij.lexer.Lexer;
import com.intellij.openapi.fileTypes.SyntaxHighlighter;
import org.jetbrains.annotations.NotNull;
import org.junit.Assert;
import org.junit.Test;

public class HighlightTest {
    @Test
    public void testLexer() {
        RobotFrameworkSyntaxHighlightingFactory factory = new RobotFrameworkSyntaxHighlightingFactory();
        @NotNull SyntaxHighlighter syntaxHightlighter = factory.getSyntaxHighlighter(null, null);
        Lexer lexer = syntaxHightlighter.getHighlightingLexer();
        lexer.start("*** Settings ***\nfoo\n");
        Assert.assertEquals("*** Settings ***", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("\n", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("foo", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("\n", lexer.getTokenText());
        lexer.advance();
        // Nothing else to match
        Assert.assertEquals("", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("", lexer.getTokenText());
    }
}
