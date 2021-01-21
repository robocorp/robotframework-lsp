package robocorp.lsp.intellij;

import org.jetbrains.annotations.NotNull;

import java.io.File;

public class Uris {

    public static String pathToUri(@NotNull String path) {
        return new File(path).toURI().toString();
    }

}
