package robocorp.lsp.intellij;

import com.intellij.lang.documentation.DocumentationProvider;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.NlsSafe;
import com.intellij.psi.PsiElement;
import com.petebevin.markdown.MarkdownProcessor;
import org.apache.commons.lang.StringEscapeUtils;
import org.eclipse.lsp4j.Hover;
import org.eclipse.lsp4j.HoverParams;
import org.eclipse.lsp4j.MarkedString;
import org.eclipse.lsp4j.MarkupContent;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
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
                CompletableFuture<Hover> future = comm.hover(new HoverParams(lspGenericPsiElement.originalId, lspGenericPsiElement.originalPos));
                if (future == null) {
                    return null;
                }
                Hover hover = future.get(Timeouts.getHoverTimeout(), TimeUnit.SECONDS);
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
                        MarkdownProcessor processor = new MarkdownProcessor();
                        return processor.markdown(mdContent);
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
