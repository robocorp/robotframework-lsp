/**
 * Original work Copyright 2000-2019 JetBrains s.r.o. (Apache 2.0)
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

import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.JarFileSystem;
import com.intellij.openapi.vfs.LocalFileSystem;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.openapi.vfs.VirtualFileSystem;
import com.intellij.xdebugger.XDebuggerUtil;
import com.intellij.xdebugger.XSourcePosition;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/**
 * Note: The debug adapter requires lines to start at 1, whereas internally lines start at 0!
 */
public class DAPPositionConverter {
    private final static String[] EGG_EXTENSIONS = new String[]{".egg", ".zip"};

    @NotNull
    public DAPSourcePosition convertToDAP(@NotNull final XSourcePosition position) {
        return new DAPSourcePosition(convertFilePath(position.getFile().getPath()), position.getLine() + 1);
    }

    @Nullable
    public XSourcePosition convertFromDAP(@NotNull final DAPSourcePosition position) {
        @Nullable VirtualFile vFile = getVirtualFile(position.getFile());
        if (vFile != null) {
            return XDebuggerUtil.getInstance().createPosition(vFile, position.getLine() - 1);
        } else {
            return null;
        }
    }

    private VirtualFile getVirtualFile(String path) {
        LocalFileSystem localFileSystem = LocalFileSystem.getInstance();
        VirtualFile vFile = localFileSystem.findFileByPath(path);

        if (vFile == null) {
            vFile = findEggEntry(localFileSystem, path);
        }
        return vFile;
    }

    public static @Nullable VirtualFile findEggEntry(@NotNull VirtualFileSystem virtualFileSystem, @NotNull String file) {
        int ind = -1;
        for (String ext : EGG_EXTENSIONS) {
            ind = file.indexOf(ext);
            if (ind != -1) {
                break;
            }
        }
        if (ind != -1) {
            String jarPath = file.substring(0, ind + 4);
            VirtualFile jarFile = virtualFileSystem.findFileByPath(jarPath);
            if (jarFile != null) {
                String innerPath = file.substring(ind + 4);
                final VirtualFile jarRoot = JarFileSystem.getInstance().getJarRootForLocalFile(jarFile);
                if (jarRoot != null) {
                    return jarRoot.findFileByRelativePath(innerPath);
                }
            }
        }
        return null;
    }

    private static String convertFilePath(String file) {
        int ind = -1;
        for (String ext : EGG_EXTENSIONS) {
            ind = file.indexOf(ext + "!");
            if (ind != -1) break;
        }
        if (ind != -1) {
            return file.substring(0, ind + 4) + file.substring(ind + 5);
        } else {
            return file;
        }
    }

    protected static String winNormCase(String file) {
        int ind = -1;
        for (String ext : EGG_EXTENSIONS) {
            ind = file.indexOf(ext);
            if (ind != -1) break;
        }
        if (ind != -1) {
            return StringUtil.toLowerCase(file.substring(0, ind + 4)) + file.substring(ind + 4);
        } else {
            return StringUtil.toLowerCase(file);
        }
    }

}
