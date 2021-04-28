/**
 * Original work Copyright JetBrains s.r.o. (Apache 2.0)
 * See ThirdPartyNotices.txt in the project root for license information.
 * All modifications Copyright (c) Robocorp Technologies Inc.
 * All rights reserved.
 * <p>
 * Licensed under the Apache License, Version 2.0 (the "License")
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * <p>
 * http: // www.apache.org/licenses/LICENSE-2.0
 * <p>
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package robocorp.dap.stack;

import org.eclipse.lsp4j.debug.StackFrame;
import org.eclipse.lsp4j.debug.StackTraceResponse;
import org.eclipse.lsp4j.debug.StoppedEventArgumentsReason;
import org.eclipse.lsp4j.debug.Thread;
import org.jetbrains.annotations.Nullable;

import java.util.ArrayList;
import java.util.List;

public class DAPThreadInfo {
    public enum State {
        RUNNING, SUSPENDED, KILLED
    }

    private final int myId;

    private List<DAPStackFrameInfo> myFrames;
    private State myState;

    // See: StoppedEventArgumentsReason
    private String myStopReason;
    private String myMessage;

    // Can be changed when a new threads request is done.
    public volatile Thread dapThread;

    public DAPThreadInfo(final int id) {
        myId = id;
    }

    public int getId() {
        return myId;
    }

    public @Nullable String getName() {
        Thread dap = dapThread;
        if (dap == null) {
            return "<Unknown>";
        }
        return dap.getName();
    }

    @Nullable
    public String getMessage() {
        return myMessage;
    }

    public void setMessage(@Nullable String message) {
        this.myMessage = message;
    }

    @Nullable
    public synchronized List<DAPStackFrameInfo> getFrames() {
        return myFrames;
    }

    public synchronized State getState() {
        return myState;
    }

    public synchronized void updateState(final State state, @Nullable final StackTraceResponse frames) {
        myState = state;
        if (frames == null) {
            myFrames = null;
            return;
        }
        StackFrame[] stackFrames = frames.getStackFrames();
        if (stackFrames == null) {
            myFrames = null;
            return;
        }
        List<DAPStackFrameInfo> stackFrameInfoList = new ArrayList<>();
        for (StackFrame f : stackFrames) {
            stackFrameInfoList.add(new DAPStackFrameInfo(
                    this.myId, f.getId(), f.getName(), new DAPSourcePosition(f.getSource().getPath(), f.getLine())));
        }
        myFrames = stackFrameInfoList;
    }

    public void setStopReason(String stopReason) {
        myStopReason = stopReason;
    }

    public boolean isStopOnBreakpoint() {
        String stop = myStopReason;
        if (stop == null) {
            return false;
        }
        switch (stop) {
            case StoppedEventArgumentsReason.BREAKPOINT:
            case StoppedEventArgumentsReason.FUNCTION_BREAKPOINT:
            case StoppedEventArgumentsReason.DATA_BREAKPOINT:
            case StoppedEventArgumentsReason.INSTRUCTION_BREAKPOINT:
                return true;
        }
        return false;
    }

    public boolean isExceptionBreak() {
        String stop = myStopReason;
        if (stop == null) {
            return false;
        }

        return stop.equals(StoppedEventArgumentsReason.EXCEPTION);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        DAPThreadInfo other = (DAPThreadInfo) o;
        return other.myId == other.myId;
    }

    @Override
    public int hashCode() {
        return Integer.hashCode(myId);
    }
}
