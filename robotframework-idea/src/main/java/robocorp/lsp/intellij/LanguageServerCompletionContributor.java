package robocorp.lsp.intellij;

import com.intellij.codeInsight.completion.CompletionContributor;
import com.intellij.codeInsight.completion.CompletionParameters;
import com.intellij.codeInsight.completion.CompletionResultSet;
import com.intellij.lang.Language;
import com.intellij.openapi.application.ex.ApplicationUtil;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.progress.ProgressIndicatorProvider;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiFile;
import org.eclipse.lsp4j.Position;
import org.jetbrains.annotations.NotNull;

public class LanguageServerCompletionContributor extends CompletionContributor {
    private static final Logger LOG = Logger.getInstance(LanguageServerCompletionContributor.class);

    @Override
    public void fillCompletionVariants(@NotNull CompletionParameters parameters, @NotNull CompletionResultSet result) {
        final Editor editor = parameters.getEditor();
        final int offset = parameters.getOffset();
        final PsiFile originalFile = parameters.getOriginalFile();
        final Language language = originalFile.getLanguage();
        if (language instanceof ILSPLanguage) {
            try {
                ApplicationUtil.runWithCheckCanceled(() -> {
                    LanguageServerDefinition languageDefinition = ((ILSPLanguage) language).getLanguageDefinition();
                    Project project = editor.getProject();
                    String basePath = project.getBasePath();
                    VirtualFile file = FileDocumentManager.getInstance().getFile(editor.getDocument());
                    if (file == null) {
                        return null;
                    }

                    LanguageServerManager instance = LanguageServerManager.getInstance("." + file.getExtension());
                    if (instance == null) {
                        // i.e.: It must be already started elsewhere.
                        return null;
                    }

                    String uri = Uris.toUri(file);
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
