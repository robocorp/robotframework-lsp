package robocorp.lsp.intellij;

import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.UserDataHolder;
import org.jetbrains.annotations.Nullable;

public interface ILSPEditor extends UserDataHolder {
    @Nullable LanguageServerDefinition getLanguageDefinition();

    @Nullable String getURI();

    /**
     * @return the extension (starting with a dot).
     */
    @Nullable String getExtension();

    @Nullable String getProjectPath();

}
