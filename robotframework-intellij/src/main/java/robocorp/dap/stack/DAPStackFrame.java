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
import com.intellij.openapi.application.ReadAction;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.ui.ColoredTextContainer;
import com.intellij.ui.SimpleTextAttributes;
import com.intellij.xdebugger.XSourcePosition;
import com.intellij.xdebugger.evaluation.XDebuggerEvaluator;
import com.intellij.xdebugger.frame.XCompositeNode;
import com.intellij.xdebugger.frame.XStackFrame;
import org.jetbrains.annotations.NotNull;
import robocorp.dap.RobotDebugProcess;

public class DAPStackFrame extends XStackFrame {
    private static final Logger LOG = Logger.getInstance(DAPStackFrame.class);

    private static final Object STACK_FRAME_EQUALITY_OBJECT = new Object();
    private final Project myProject;
    private final RobotDebugProcess myDebugProcess;
    private final DAPStackFrameInfo myFrameInfo;
    private final XSourcePosition myPosition;

    public DAPStackFrame(@NotNull Project project,
                         @NotNull final RobotDebugProcess debugProcess,
                         @NotNull final DAPStackFrameInfo frameInfo,
                         XSourcePosition position) {
        myProject = project;
        myDebugProcess = debugProcess;
        myFrameInfo = frameInfo;
        myPosition = position;
    }

    @Override
    public Object getEqualityObject() {
        return STACK_FRAME_EQUALITY_OBJECT;
    }

    @Override
    public XSourcePosition getSourcePosition() {
        return myPosition;
    }

    @Override
    public XDebuggerEvaluator getEvaluator() {
        return null;
    }

    @Override
    public void customizePresentation(@NotNull ColoredTextContainer component) {
        component.setIcon(AllIcons.Debugger.Frame);

        if (myPosition == null) {
            component.append("Stack frame not available.", SimpleTextAttributes.GRAY_ATTRIBUTES);
            return;
        }

        final VirtualFile file = myPosition.getFile();
        boolean isExternal =
                ReadAction.compute(() -> {

                    final Document document = FileDocumentManager.getInstance().getDocument(file);
                    if (document != null) {
                        return !ProjectRootManager.getInstance(myProject).getFileIndex().isInContent(file);
                    } else {
                        return true;
                    }
                });

        component.append(myFrameInfo.getName(), gray(isExternal));
        component.append(", ", gray(isExternal));
        component.append(myPosition.getFile().getName(), gray(isExternal));
        component.append(":", gray(isExternal));
        component.append(Integer.toString(myPosition.getLine() + 1), gray(isExternal));
    }

    protected static SimpleTextAttributes gray(boolean gray) {
        return (gray) ? SimpleTextAttributes.GRAYED_ATTRIBUTES : SimpleTextAttributes.REGULAR_ATTRIBUTES;
    }

    @Override
    public void computeChildren(@NotNull final XCompositeNode node) {
//        if (node.isObsolete()) return;
//        ApplicationManager.getApplication().executeOnPooledThread(() -> {
//            try {
//                boolean cached = myDebugProcess.isFrameCached(this);
//                XValueChildrenList values = myDebugProcess.loadFrame(this);
//                if (!node.isObsolete()) {
//                    addChildren(node, values);
//                }
//                if (values != null && !cached) {
//                    PyDebugValue.getAsyncValues(this, myDebugProcess, values);
//                }
//            } catch (PyDebuggerException e) {
//                if (!node.isObsolete()) {
//                    node.setErrorMessage("Error: unable to display frame variables.");
//                }
//                LOG.warn(e);
//            }
//        });
    }

    @NotNull
    public String getName() {
        return myFrameInfo.getName();
    }

}
