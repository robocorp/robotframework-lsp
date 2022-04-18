package robocorp.robot.intellij;

import com.intellij.openapi.progress.ProcessCanceledException;

public class CancelledException extends Exception {
    public CancelledException(ProcessCanceledException e) {
        super(e);
    }
}
