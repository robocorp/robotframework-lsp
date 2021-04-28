/**
 * Original work Copyright 2000-2016 JetBrains s.r.o. (Apache 2.0)
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

import com.intellij.xdebugger.frame.XExecutionStack;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.dap.RobotDebugProcess;

import javax.swing.*;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Objects;

public class DAPExecutionStack extends XExecutionStack {

    private final RobotDebugProcess myDebugProcess;
    private final DAPThreadInfo myThreadInfo;
    private DAPStackFrame myTopFrame;

    public DAPExecutionStack(@NotNull final RobotDebugProcess debugProcess, @NotNull final DAPThreadInfo threadInfo, final @Nullable Icon icon) {
        super(threadInfo.getName(), icon); //NON-NLS
        myDebugProcess = debugProcess;
        myThreadInfo = threadInfo;
    }

    @Override
    public DAPStackFrame getTopFrame() {
        if (myTopFrame == null) {
            final List<DAPStackFrameInfo> frames = myThreadInfo.getFrames();
            if (frames != null) {
                myTopFrame = convert(myDebugProcess, frames.get(0));
            }
        }
        return myTopFrame;
    }

    @Override
    public void computeStackFrames(int firstFrameIndex, XStackFrameContainer container) {
        if (myThreadInfo.getState() != DAPThreadInfo.State.SUSPENDED) {
            container.errorOccurred("Frame not available (not in suspended state).");
            return;
        }

        final List<DAPStackFrameInfo> frames = myThreadInfo.getFrames();
        if (frames != null && firstFrameIndex <= frames.size()) {
            final List<DAPStackFrame> xFrames = new LinkedList<>();
            for (int i = firstFrameIndex; i < frames.size(); i++) {
                xFrames.add(convert(myDebugProcess, frames.get(i)));
            }
            container.addStackFrames(xFrames, true);
        } else {
            container.addStackFrames(Collections.emptyList(), true);
        }
    }

    private static DAPStackFrame convert(final RobotDebugProcess debugProcess, final DAPStackFrameInfo frameInfo) {
        return debugProcess.createStackFrame(frameInfo);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) {
            return false;
        }

        DAPExecutionStack that = (DAPExecutionStack) o;

        if (!Objects.equals(myThreadInfo, that.myThreadInfo)) {
            return false;
        }

        return true;
    }

    @Override
    public int hashCode() {
        return myThreadInfo != null ? myThreadInfo.hashCode() : 0;
    }

}
