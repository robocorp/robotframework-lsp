/**
 * Original work Copyright 2000-2020 JetBrains s.r.o. (Apache 2.0)
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

import com.intellij.icons.AllIcons;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.xdebugger.frame.XExecutionStack;
import com.intellij.xdebugger.frame.XSuspendContext;
import org.jetbrains.annotations.NotNull;
import robocorp.dap.RobotDebugProcess;

import javax.swing.*;
import java.util.Collection;

public class DAPSuspendContext extends XSuspendContext {

    private static final Logger LOG = Logger.getInstance(DAPSuspendContext.class);

    private final DAPExecutionStack myActiveStack;
    private final RobotDebugProcess myDebugProcess;

    public DAPSuspendContext(@NotNull final RobotDebugProcess debugProcess, @NotNull final DAPThreadInfo threadInfo) {
        myDebugProcess = debugProcess;
        myActiveStack = new DAPExecutionStack(debugProcess, threadInfo, getThreadIcon(threadInfo));
    }

    @Override
    @NotNull
    public DAPExecutionStack getActiveExecutionStack() {
        return myActiveStack;
    }

    @NotNull
    public static Icon getThreadIcon(@NotNull DAPThreadInfo threadInfo) {
        if ((threadInfo.getState() == DAPThreadInfo.State.SUSPENDED) && threadInfo.isStopOnBreakpoint()) {
            return AllIcons.Debugger.ThreadAtBreakpoint;
        } else {
            return AllIcons.Debugger.ThreadSuspended;
        }
    }

    @Override
    public XExecutionStack @NotNull [] getExecutionStacks() {
        final Collection<DAPThreadInfo> threads = myDebugProcess.getThreads();
        if (threads.size() < 1) {
            return XExecutionStack.EMPTY_ARRAY;
        } else {
            XExecutionStack[] stacks = new XExecutionStack[threads.size()];
            int i = 0;
            for (DAPThreadInfo thread : threads) {
                stacks[i++] = new DAPExecutionStack(myDebugProcess, thread, getThreadIcon(thread));
            }
            return stacks;
        }
    }

}
