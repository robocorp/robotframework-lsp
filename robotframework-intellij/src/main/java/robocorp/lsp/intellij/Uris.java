package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.vfs.VirtualFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.File;
import java.net.URI;
import java.net.URISyntaxException;

public class Uris {

    private static final Logger LOG = Logger.getInstance(Uris.class);

    public static @NotNull String pathToUri(@NotNull String path) {
        return new File(path).toURI().toString();
    }

    public static @Nullable String toUri(@NotNull Editor editor) {
        VirtualFile file = FileDocumentManager.getInstance().getFile(editor.getDocument());
        if (file == null) {
            LOG.info("No file for editor: " + editor);
            return null;
        }
        return toUri(file);
    }

    public static @NotNull String toUri(VirtualFile file) {
        return pathToUri(file.getPath());
    }

    public static @NotNull String toUri(File file) {
        return file.toURI().toString();
    }

    public static @Nullable File toFile(String uri) {
        try {
            return new File(new URI(uri));
        } catch (URISyntaxException e) {
            LOG.error("Error converting uri: " + uri, e);
            return null;
        }
    }
}
