package robocorp.lsp.intellij;

import com.intellij.testFramework.fixtures.BasePlatformTestCase;
import com.intellij.testFramework.fixtures.TempDirTestFixture;
import com.intellij.testFramework.fixtures.impl.TempDirTestFixtureImpl;

import java.io.IOException;

public abstract class LSPTesCase extends BasePlatformTestCase {
    @Override
    protected String getTestDataPath() {
        return "src/test/resources";
    }

    @Override
    protected TempDirTestFixture createTempDirTestFixture() {
        return new TempDirTestFixtureImpl() {
            @Override
            public void tearDown() throws Exception {
                try {
                    LanguageServerManager.disposeAll();
                    super.tearDown();
                } catch (IOException e) {
                    // Ignore if unable to delete on teardown.
                }
            }
        };
    }

}
