package robotframework.idea;

import com.intellij.lexer.Lexer;
import com.intellij.openapi.fileTypes.SyntaxHighlighter;
import com.intellij.testFramework.fixtures.BasePlatformTestCase;
import org.jetbrains.annotations.NotNull;
import org.junit.Assert;
import org.junit.Test;

public class HighlightTest {
    @Test
    public void testHightlight() {
        RobotFrameworkSyntaxHighlightingFactory factory = new RobotFrameworkSyntaxHighlightingFactory();
        @NotNull SyntaxHighlighter syntaxHightlighter = factory.getSyntaxHighlighter(null, null);
        Lexer lexer = syntaxHightlighter.getHighlightingLexer();
        lexer.start("*** Settings ***\nfoo\n");
        lexer.advance();
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
