package robocorp.dap.stack;

import com.intellij.openapi.util.NlsSafe;

public class DAPStackFrameInfo {

    private final int myThreadId;
    private final int myId;
    private final String myName;
    private final DAPSourcePosition myPosition;

    public DAPStackFrameInfo(final int threadId, final int id, @NlsSafe final String name, final DAPSourcePosition position) {
        myThreadId = threadId;
        myId = id;
        myName = name;
        myPosition = position;
    }

    public int getThreadId() {
        return myThreadId;
    }

    public int getId() {
        return myId;
    }

    @NlsSafe
    public String getName() {
        return myName;
    }

    public DAPSourcePosition getPosition() {
        return myPosition;
    }
}
