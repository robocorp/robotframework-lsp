package robocorp.lsp.intellij;

import com.intellij.codeInsight.completion.CompletionContributor;
import com.intellij.codeInsight.completion.CompletionParameters;
import com.intellij.codeInsight.completion.CompletionResultSet;
import com.intellij.openapi.application.ex.ApplicationUtil;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.progress.ProgressIndicatorProvider;
import com.intellij.openapi.project.Project;
import com.intellij.psi.PsiFile;
import org.eclipse.lsp4j.Position;
import org.jetbrains.annotations.NotNull;

public class FeatureCodeCompletion extends CompletionContributor {
    private static final Logger LOG = Logger.getInstance(FeatureCodeCompletion.class);

    @Override
    public void fillCompletionVariants(@NotNull CompletionParameters parameters, @NotNull CompletionResultSet result) {
        final Editor editor = parameters.getEditor();
        final int offset = parameters.getOffset();
        final EditorLanguageServerConnection editorLanguageServerConnection = EditorLanguageServerConnection.getFromUserData(editor);
        final PsiFile originalFile = parameters.getOriginalFile();
        if (editorLanguageServerConnection != null) {
            try {
                ApplicationUtil.runWithCheckCanceled(() -> {
                    Project project = editor.getProject();
                    String basePath = project.getBasePath();
                    String uri = editorLanguageServerConnection.getURI();
                    Position serverPos = EditorUtils.offsetToLSPPos(editor, offset);
                    String txt = originalFile.getNode().getText();
                    return null;
                }, ProgressIndicatorProvider.getGlobalProgressIndicator());
            } catch (ProcessCanceledException ignored) {
                // ProcessCanceledException can be ignored.
            } catch (Exception e) {
                LOG.error("LSP Completions ended with an error", e);
            }
        }
    }

}
