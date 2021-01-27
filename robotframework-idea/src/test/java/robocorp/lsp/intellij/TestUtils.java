package robocorp.lsp.intellij;

import org.junit.Assert;

public class TestUtils {
    public interface ICondition<T> {
        public T check();
    }

    /**
     * Wait until a non-null value is returned from the condition.
     */
    public static <T> T waitForCondition(ICondition<T> condition) {
        long initialTime = System.currentTimeMillis();

        while (System.currentTimeMillis() < initialTime + 2000) {
            T check = condition.check();
            if (check != null) {
                return check;
            }
            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                // Ignore
            }
        }

        throw new AssertionError("Error. Condition not satisfied during the available time.");
    }
}
