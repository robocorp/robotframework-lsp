package robocorp.robot.intellij;

import com.intellij.lexer.Lexer;
import com.intellij.openapi.fileTypes.SyntaxHighlighter;
import org.jetbrains.annotations.NotNull;
import org.junit.Assert;
import org.junit.Test;
import robocorp.lsp.intellij.LSPTesCase;

public class HighlightTest extends LSPTesCase {
    @Test
    public void testLexer() {
        RobotFrameworkSyntaxHighlightingFactory factory = new RobotFrameworkSyntaxHighlightingFactory();
        @NotNull SyntaxHighlighter syntaxHighlighter = factory.getSyntaxHighlighter(null, null);
        Lexer lexer = syntaxHighlighter.getHighlightingLexer();
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

    @Test
    public void testLexerVars() {
        RobotFrameworkSyntaxHighlightingFactory factory = new RobotFrameworkSyntaxHighlightingFactory();
        @NotNull SyntaxHighlighter syntaxHighlighter = factory.getSyntaxHighlighter(null, null);
        Lexer lexer = syntaxHighlighter.getHighlightingLexer();
        lexer.start("Some ${v ar} foo\n");
        Assert.assertEquals("Some", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals(" ", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("${v ar}", lexer.getTokenText());
        Assert.assertEquals(RobotElementType.VARIABLE, lexer.getTokenType());
        lexer.advance();
        Assert.assertEquals(" ", lexer.getTokenText());
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

    @Test
    public void testLexerVars2() {
        RobotFrameworkSyntaxHighlightingFactory factory = new RobotFrameworkSyntaxHighlightingFactory();
        @NotNull SyntaxHighlighter syntaxHighlighter = factory.getSyntaxHighlighter(null, null);
        Lexer lexer = syntaxHighlighter.getHighlightingLexer();
        lexer.start("Some${var}foo\n");
        Assert.assertEquals("Some", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("${var}", lexer.getTokenText());
        Assert.assertEquals(RobotElementType.VARIABLE, lexer.getTokenType());
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

    @Test
    public void testLexerVars3() {
        RobotFrameworkSyntaxHighlightingFactory factory = new RobotFrameworkSyntaxHighlightingFactory();
        @NotNull SyntaxHighlighter syntaxHighlighter = factory.getSyntaxHighlighter(null, null);
        Lexer lexer = syntaxHighlighter.getHighlightingLexer();
        lexer.start("Log    some=${HEADLESS}\n");
        Assert.assertEquals("Log", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("    ", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("some=", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("${HEADLESS}", lexer.getTokenText());
        Assert.assertEquals(RobotElementType.VARIABLE, lexer.getTokenType());
        lexer.advance();
        Assert.assertEquals("\n", lexer.getTokenText());
        lexer.advance();
        // Nothing else to match
        Assert.assertEquals("", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("", lexer.getTokenText());
    }

    @Test
    public void testLexerComments() {
        RobotFrameworkSyntaxHighlightingFactory factory = new RobotFrameworkSyntaxHighlightingFactory();
        @NotNull SyntaxHighlighter syntaxHighlighter = factory.getSyntaxHighlighter(null, null);
        Lexer lexer = syntaxHighlighter.getHighlightingLexer();
        lexer.start("*** Settings ***\n#Comment\n");
        Assert.assertEquals("*** Settings ***", lexer.getTokenText());
        Assert.assertEquals(RobotElementType.HEADING, lexer.getTokenType());
        lexer.advance();
        Assert.assertEquals("\n", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("#Comment", lexer.getTokenText());
        Assert.assertEquals(RobotElementType.COMMENT, lexer.getTokenType());
        lexer.advance();
        Assert.assertEquals("\n", lexer.getTokenText());
        lexer.advance();
        // Nothing else to match
        Assert.assertEquals("", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("", lexer.getTokenText());
    }

    @Test
    public void testLexerComments2() {
        RobotFrameworkSyntaxHighlightingFactory factory = new RobotFrameworkSyntaxHighlightingFactory();
        @NotNull SyntaxHighlighter syntaxHighlighter = factory.getSyntaxHighlighter(null, null);
        Lexer lexer = syntaxHighlighter.getHighlightingLexer();
        lexer.start("\n  #Comment\n");
        Assert.assertEquals("\n", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("  ", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("#Comment", lexer.getTokenText());
        Assert.assertEquals(RobotElementType.COMMENT, lexer.getTokenType());
        lexer.advance();
        Assert.assertEquals("\n", lexer.getTokenText());
        lexer.advance();
        // Nothing else to match
        Assert.assertEquals("", lexer.getTokenText());
        lexer.advance();
        Assert.assertEquals("", lexer.getTokenText());
    }
}
