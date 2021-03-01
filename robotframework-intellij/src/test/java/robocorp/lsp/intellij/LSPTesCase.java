package robocorp.lsp.intellij;

import com.intellij.testFramework.fixtures.BasePlatformTestCase;
import com.intellij.testFramework.fixtures.TempDirTestFixture;
import com.intellij.testFramework.fixtures.impl.TempDirTestFixtureImpl;
import robocorp.robot.intellij.RobotFrameworkLanguage;

import java.io.File;
import java.io.IOException;

public abstract class LSPTesCase extends BasePlatformTestCase {

    @Override
    protected void setUp() throws Exception {
        super.setUp();
        String tempDirPath = myFixture.getTempDirPath();
        File file = new File(tempDirPath, ".user_home");
        RobotFrameworkLanguage.INSTANCE.setRobotFrameworkLSUserHome(file.toString());
    }

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
