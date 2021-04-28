package robocorp.dap.stack;

import com.intellij.openapi.util.SystemInfo;
import com.intellij.openapi.util.io.FileUtil;
import org.jetbrains.annotations.Nullable;

import java.util.Objects;

public class DAPSourcePosition {

    private final String file;
    // Note: this line is 1-based
    private final int line;

    /**
     * Be careful: this line is 1-based, whereas in general Intellij has things as 0-based
     * (use only to construct a line which comes from the debug adapter, which is 1-based).
     */
    protected DAPSourcePosition(final String file, final int line) {
        this.file = normalize(file);
        this.line = line;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof DAPSourcePosition)) {
            return false;
        }
        DAPSourcePosition that = (DAPSourcePosition) o;
        return line == that.line && Objects.equals(file, that.file);
    }

    @Override
    public int hashCode() {
        return Objects.hash(file, line);
    }

    @Nullable
    protected String normalize(@Nullable String file) {
        if (file == null) {
            return null;
        }

        if (SystemInfo.isWindows) {
            file = DAPPositionConverter.winNormCase(file);
        }
        return FileUtil.toSystemIndependentName(file);
    }

    public String getFile() {
        return file;
    }

    public int getLine() {
        return line;
    }

    @Override
    public String toString() {
        return "DAPSourcePosition(" + file + ":" + line + ")";
    }

}
