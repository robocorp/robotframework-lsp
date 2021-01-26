package robocorp.lsp.intellij;

import com.intellij.openapi.editor.Document;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.UserDataHolder;
import org.eclipse.lsp4j.Diagnostic;
import org.eclipse.lsp4j.Position;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;

public interface ILSPEditor extends UserDataHolder {
    @Nullable LanguageServerDefinition getLanguageDefinition();

    @Nullable String getURI();

    /**
     * @return the extension (starting with a dot).
     */
    @Nullable String getExtension();

    @Nullable String getProjectPath();

    Position offsetToLSPPos(int offset);

    int LSPPosToOffset(Position pos);

    String getText();

    Document getDocument();

    void setDiagnostics(@NotNull List<Diagnostic> diagnostics);

    @NotNull List<Diagnostic> getDiagnostics();
}
