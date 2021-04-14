package robocorp.lsp.intellij;

import com.intellij.lang.annotation.AnnotationBuilder;
import com.intellij.lang.annotation.AnnotationHolder;
import com.intellij.lang.annotation.ExternalAnnotator;
import com.intellij.lang.annotation.HighlightSeverity;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.editor.event.DocumentListener;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.TextRange;
import com.intellij.psi.PsiFile;
import org.eclipse.lsp4j.Position;
import org.eclipse.lsp4j.SemanticTokens;
import org.eclipse.lsp4j.SemanticTokensLegend;
import org.eclipse.lsp4j.SemanticTokensWithRegistrationOptions;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.robot.intellij.RobotFrameworkSyntaxHighlightingFactory;

import java.util.Iterator;
import java.util.List;
import java.util.concurrent.CancellationException;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.TimeUnit;

public class FeatureSemanticHighlighting extends ExternalAnnotator<EditorLanguageServerConnection, Pair<SemanticTokens, EditorLanguageServerConnection>> {

    private static final Logger LOG = Logger.getInstance(FeatureSemanticHighlighting.class);

    @Override
    public @Nullable EditorLanguageServerConnection collectInformation(@NotNull PsiFile file, @NotNull Editor editor, boolean hasErrors) {
        EditorLanguageServerConnection editorLanguageServerConnection = EditorLanguageServerConnection.getFromUserData(editor);
        return editorLanguageServerConnection;
    }

    @Override
    public @Nullable Pair<SemanticTokens, EditorLanguageServerConnection> doAnnotate(EditorLanguageServerConnection connection) {
        try {
            CompletableFuture<SemanticTokens> semanticTokens = connection.getSemanticTokens();
            if (semanticTokens == null) {
                return null;
            }
            DocumentListener listener = new DocumentListener() {
                @Override
                public void beforeDocumentChange(@NotNull DocumentEvent event) {
                    try {
                        semanticTokens.cancel(true);
                    } catch (ProcessCanceledException | CompletionException | CancellationException e) {
                        // ignore
                    }
                }
            };
            Document document = connection.getEditor().getDocument();
            if (document != null) {
                document.addDocumentListener(listener);
            }
            try {
                SemanticTokens tokens = semanticTokens.get(Timeouts.getSemanticHighlightingTimeout(), TimeUnit.SECONDS);
                if (tokens == null) {
                    return null;
                }
                return Pair.create(tokens, connection);
            } catch (ProcessCanceledException | CompletionException | CancellationException | InterruptedException ignored) {
                // Cancelled (InterruptedException is thrown when completion.cancel(true) is called from another thread).
                return null;
            } finally {
                if (document != null) {
                    document.removeDocumentListener(listener);
                }
            }
        } catch (Exception e) {
            LOG.error("Unable to compute semantic tokens.", e);
            return null;
        }
    }

    @Override
    public void apply(@NotNull PsiFile
                              file, Pair<SemanticTokens, EditorLanguageServerConnection> pair, @NotNull AnnotationHolder holder) {
        if (pair == null) {
            return;
        }
        ILSPEditor editor = pair.second.getEditor();
        if (editor == null) {
            return;
        }

        Document document = editor.getDocument();
        if (document == null) {
            return;
        }

        int textLength = document.getTextLength();

        SemanticTokensWithRegistrationOptions semanticTokensProvider = pair.second.getSemanticTokensProvider();
        SemanticTokensLegend legend = semanticTokensProvider.getLegend();
        List<String> tokenTypes = legend.getTokenTypes();

        List<Integer> data = pair.first.getData();
        Iterator<Integer> iterator = data.iterator();
        int line = 0;
        int col = 0;
        Position pos = new Position();
        while (iterator.hasNext()) {
            Integer lineDelta = iterator.next();
            Integer colDelta = iterator.next();
            Integer tokenLen = iterator.next();
            Integer tokenType = iterator.next();
            Integer tokenModifier = iterator.next();
            line += lineDelta;
            if (lineDelta == 0) {
                col += colDelta;
            } else {
                col = colDelta;
            }
            pos.setLine(line);
            pos.setCharacter(col);
            int startOffset = editor.LSPPosToOffset(pos);
            int endOffset = startOffset + tokenLen;

            if (startOffset < 0) {
                // out of sync
                break;
            }

            try {
                if (endOffset > textLength) {
                    break;
                }
                AnnotationBuilder range = holder.newSilentAnnotation(HighlightSeverity.INFORMATION).range(new TextRange(startOffset, endOffset));
                range.textAttributes(RobotFrameworkSyntaxHighlightingFactory.getFromType(tokenTypes.get(tokenType))).create();
            } catch (Exception e) {
                LOG.error(e);
            }
        }
    }
}
