package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.testFramework.fixtures.BasePlatformTestCase;
import org.jetbrains.annotations.NotNull;
import org.junit.Assert;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

public class SymbolsTest extends BasePlatformTestCase {
    private static final Logger LOG = Logger.getInstance(SymbolsTest.class);

    @Override
    protected String getTestDataPath() {
        return "src/test/resources";
    }

    @Test
    public void testSymbols() throws Exception {
        // Note: this test would fail if NO_FS_ROOTS_ACCESS_CHECK is not set to true (because
        // we access symbols out of the FS root).
        myFixture.configureByFile("case1.robot");
        Editor editor = myFixture.getEditor();

        FeatureSymbols featureSymbols = new FeatureSymbols();
        @NotNull GlobalSearchScope searchScope = new GlobalSearchScope(editor.getProject()) {
            @Override
            public boolean isSearchInModuleContent(@NotNull Module aModule) {
                return false;
            }

            @Override
            public boolean isSearchInLibraries() {
                return true;
            }

            @Override
            public boolean contains(@NotNull VirtualFile file) {
                return true;
            }
        };
        final List<String> lst = new ArrayList<>();
        featureSymbols.processNames(s -> {
            lst.add(s);
            return true;
        }, searchScope, null);

        if (lst.size() < 10) {
            Assert.fail("Expected more than 10 elements. Found: " + lst);
        }
    }
}
