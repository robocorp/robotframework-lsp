package robocorp.lsp.intellij;

import com.intellij.lang.annotation.AnnotationHolder;
import com.intellij.lang.annotation.ExternalAnnotator;
import com.intellij.lang.annotation.HighlightSeverity;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.util.TextRange;
import com.intellij.psi.PsiFile;
import org.eclipse.lsp4j.Diagnostic;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;

public class FeatureDiagnostics extends ExternalAnnotator<EditorLanguageServerConnection, EditorLanguageServerConnection> {
    private static final Logger LOG = Logger.getInstance(FeatureDiagnostics.class);

    @Nullable
    @Override
    public EditorLanguageServerConnection collectInformation(@NotNull PsiFile file, @NotNull Editor editor, boolean hasErrors) {
        EditorLanguageServerConnection editorLanguageServerConnection = EditorLanguageServerConnection.getFromUserData(editor);
        return editorLanguageServerConnection;
    }

    @Override
    public @Nullable EditorLanguageServerConnection doAnnotate(EditorLanguageServerConnection editorLanguageServerConnection) {
        return editorLanguageServerConnection;
    }

    @Override
    public void apply(@NotNull PsiFile file, EditorLanguageServerConnection editorLanguageServerConnection, @NotNull AnnotationHolder holder) {
        List<Diagnostic> diagnostics = editorLanguageServerConnection.getDiagnostics();
        for (Diagnostic diagnostic : diagnostics) {
            int startOffset = editorLanguageServerConnection.LSPPosToOffset(diagnostic.getRange().getStart());
            int endOffset = editorLanguageServerConnection.LSPPosToOffset(diagnostic.getRange().getEnd());

            HighlightSeverity severity;
            switch (diagnostic.getSeverity()) {
                case Warning:
                    severity = HighlightSeverity.WARNING;
                    break;
                case Information:
                case Hint:
                    severity = HighlightSeverity.INFORMATION;
                    break;
                default:
                    severity = HighlightSeverity.ERROR;
                    break;
            }

            holder.newAnnotation(severity, diagnostic.getMessage()).range(new TextRange(startOffset, endOffset)).create();
        }
    }
}
