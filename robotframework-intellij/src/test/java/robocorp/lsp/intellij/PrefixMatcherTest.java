package robocorp.lsp.intellij;

import junit.framework.TestCase;
import org.junit.Test;

public class PrefixMatcherTest extends TestCase {

    @Test
    public void testPrefixMatcher() throws Exception {
        String prefix = FeatureCodeCompletion.LSPPrefixMatcher.getPrefix("   Check this");
        assertEquals("Check this", prefix);

        prefix = FeatureCodeCompletion.LSPPrefixMatcher.getPrefix("   Check this ");
        assertEquals("Check this ", prefix);

        prefix = FeatureCodeCompletion.LSPPrefixMatcher.getPrefix("   Check this  ");
        assertEquals("", prefix);

        prefix = FeatureCodeCompletion.LSPPrefixMatcher.getPrefix("   } this");
        assertEquals("this", prefix);

        prefix = FeatureCodeCompletion.LSPPrefixMatcher.getPrefix(" ${th");
        assertEquals("${th", prefix);

        prefix = FeatureCodeCompletion.LSPPrefixMatcher.getPrefix("Some.call");
        assertEquals("call", prefix);
    }
}
