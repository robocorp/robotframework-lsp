package robocorp.lsp.intellij;

import com.intellij.lang.documentation.DocumentationProvider;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.NlsSafe;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import org.commonmark.node.*;
import org.commonmark.parser.Parser;
import org.commonmark.renderer.html.HtmlRenderer;
import org.apache.commons.lang.StringEscapeUtils;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.psi.LSPGenericPsiElement;

import java.util.Iterator;
import java.util.List;
import java.util.concurrent.*;

public class FeatureHover implements DocumentationProvider {

    private static final Logger LOG = Logger.getInstance(FeatureHover.class);

    public FeatureHover() {
    }

    @Override
    public @Nullable PsiElement getCustomDocumentationElement(@NotNull Editor editor, @NotNull PsiFile file, @Nullable PsiElement contextElement, int targetOffset) {
        return new LSPGenericPsiElement(editor.getProject(), file, contextElement.getText(), targetOffset, targetOffset);
    }

    @Override
    public @Nullable @NlsSafe String generateDoc(PsiElement element, @Nullable PsiElement originalElement) {
        if (element instanceof LSPGenericPsiElement) {
            LSPGenericPsiElement lspGenericPsiElement = (LSPGenericPsiElement) element;
            Project project = lspGenericPsiElement.getProject();
            LanguageServerDefinition languageDefinition = lspGenericPsiElement.languageDefinition;
            LanguageServerManager languageServerManager = LanguageServerManager.getInstance(languageDefinition);

            String basePath = project.getBasePath();
            if (basePath == null) {
                return null;
            }

            try {
                LanguageServerCommunication comm = languageServerManager.getLanguageServerCommunication(languageDefinition.ext.iterator().next(), basePath, project);
                if (comm == null) {
                    return null;
                }
                CompletableFuture<Hover> future;
                if (lspGenericPsiElement.originalId != null && lspGenericPsiElement.originalPos != null) {
                    future = comm.hover(new HoverParams(lspGenericPsiElement.originalId, lspGenericPsiElement.originalPos));
                } else {
                    VirtualFile virtualFile = element.getContainingFile().getVirtualFile();
                    String uri = Uris.toUri(virtualFile);
                    final TextDocumentIdentifier textDocument = new TextDocumentIdentifier(uri);
                    Document document = FileDocumentManager.getInstance().getDocument(virtualFile);
                    final Position position = EditorUtils.offsetToLSPPos(document, ((LSPGenericPsiElement) element).startOffset);
                    future = comm.hover(new HoverParams(textDocument, position));
                }
                if (future == null) {
                    return null;
                }
                Hover hover = future.get(Timeouts.getHoverTimeout(), TimeUnit.SECONDS);
                if (hover == null) {
                    return null;
                }
                Either<List<Either<String, MarkedString>>, MarkupContent> contents = hover.getContents();
                if (contents.isLeft()) {
                    List<Either<String, MarkedString>> left = contents.getLeft();
                    Iterator<Either<String, MarkedString>> iterator = left.iterator();
                    while (iterator.hasNext()) {
                        FastStringBuffer buf = new FastStringBuffer();
                        Either<String, MarkedString> next = iterator.next();
                        if (next.isLeft()) {
                            buf.append(StringEscapeUtils.escapeHtml(next.getLeft()));
                        } else {
                            MarkedString right = next.getRight();
                            // Could be better (but it's deprecated anyways, so, don't bother).
                            buf.append(StringEscapeUtils.escapeHtml(right.getValue()));
                        }
                        buf.append('\n');
                    }

                } else if (contents.isRight()) {
                    MarkupContent right = contents.getRight();
                    if ("markdown".equals(right.getKind())) {
                        String mdContent = right.getValue();
                        Parser parser = Parser.builder().build();
                        Node document = parser.parse(mdContent);
                        HtmlRenderer renderer = HtmlRenderer.builder().build();
                        return renderer.render(document);
                    } else {
                        return StringEscapeUtils.escapeHtml(right.getValue());
                    }
                }
            } catch (ProcessCanceledException | CompletionException | CancellationException | InterruptedException | TimeoutException e) {
                // If it was cancelled, just ignore it (don't log).
            } catch (Exception e) {
                LOG.error(e);
            }
        }
        return null;
    }

    @Override
    public @Nullable String getQuickNavigateInfo(PsiElement element, PsiElement originalElement) {
        if (element != null) {
            return element.toString();
        }
        return null;
    }
}
