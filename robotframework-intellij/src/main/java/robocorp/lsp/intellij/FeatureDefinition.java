package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.TextRange;
import com.intellij.openapi.vfs.LocalFileSystem;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.psi.LSPGenericPsiElement;
import robocorp.lsp.psi.LSPPsiAstElement;

import java.io.File;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

/**
 * The parser (instance of com.intellij.lang.ParserDefinition) must generate LSPPsiAstElement
 * elements so that the go to definition works!
 */
public class FeatureDefinition {

    private static final Logger LOG = Logger.getInstance(FeatureDefinition.class);

    public static @Nullable PsiElement resolve(LSPPsiAstElement.LSPReference reference) {
        PsiElement element = reference.getElement();
        PsiFile psiFile = element.getContainingFile();
        if (psiFile == null) {
            return null;
        }
        @NotNull Project project = element.getProject();
        VirtualFile virtualFile = psiFile.getVirtualFile();
        if (virtualFile == null) {
            return null;
        }
        String basePath = project.getBasePath();
        if (basePath == null) {
            return null;
        }
        LanguageServerDefinition languageDefinition = EditorUtils.getLanguageDefinition(virtualFile);
        if (languageDefinition == null) {
            return null;
        }
        LanguageServerManager languageServerManager = LanguageServerManager.getInstance(languageDefinition);
        try {
            LanguageServerCommunication comm = languageServerManager.getLanguageServerCommunication(languageDefinition.ext.iterator().next(), basePath);
            if (comm == null) {
                return null;
            }
            String uri = Uris.toUri(virtualFile);
            TextRange absoluteRange = reference.getAbsoluteRange();
            Document document = FileDocumentManager.getInstance().getDocument(virtualFile);
            if (document == null) {
                return null;
            }
            Position pos = EditorUtils.offsetToLSPPos(document, absoluteRange.getStartOffset());
            TextDocumentIdentifier textDocumentIdentifier = new TextDocumentIdentifier(uri);
            DefinitionParams params = new DefinitionParams(textDocumentIdentifier, pos);
            CompletableFuture<Either<List<? extends Location>, List<? extends LocationLink>>> definition = comm.definition(params);
            if (definition == null) {
                return null;
            }

            Either<List<? extends Location>, List<? extends LocationLink>> listListEither = definition.get(
                    Timeouts.getDefinitionTimeout(), TimeUnit.SECONDS);
            if (listListEither == null) {
                return null;
            }

            String targetUri;
            Range targetRange;
            if (listListEither.isLeft()) {
                List<? extends Location> left = listListEither.getLeft();
                if (left.size() > 0) {
                    Location location = left.get(0);
                    targetUri = location.getUri();
                    targetRange = location.getRange();
                } else {
                    return null;
                }
            } else if (listListEither.isRight()) {
                List<? extends LocationLink> right = listListEither.getRight();
                if (right.size() > 0) {
                    LocationLink locationLink = right.get(0);
                    targetUri = locationLink.getTargetUri();
                    targetRange = locationLink.getTargetSelectionRange();
                } else {
                    return null;
                }
            } else {
                return null;
            }
            File targetFile = Uris.toFile(targetUri);
            if (targetFile == null) {
                return null;
            }

            VirtualFile targetVirtualFile = LocalFileSystem.getInstance().findFileByIoFile(targetFile);
            if (targetVirtualFile == null) {
                return null;
            }
            PsiFile targetPsiFile = EditorUtils.getPSIFile(project, targetVirtualFile);
            if (targetPsiFile == null) {
                return null;
            }
            Document targetDocument = FileDocumentManager.getInstance().getDocument(targetVirtualFile);
            if (targetDocument == null) {
                return null;
            }
            int startOffset = EditorUtils.LSPPosToOffset(targetDocument, targetRange.getStart());
            int endOffset = EditorUtils.LSPPosToOffset(targetDocument, targetRange.getEnd());

            String text = targetDocument.getText(new TextRange(startOffset, endOffset));
            return new LSPGenericPsiElement(project, targetPsiFile, text, startOffset, endOffset);
        } catch (ProcessCanceledException e) {
            // If it was cancelled, just ignore it (don't log).
        } catch (Exception e) {
            LOG.error(e);
        }

        return null;
    }

}
