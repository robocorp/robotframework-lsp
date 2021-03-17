package robocorp.lsp.intellij;

import com.intellij.lang.annotation.AnnotationBuilder;
import com.intellij.lang.annotation.AnnotationHolder;
import com.intellij.lang.annotation.ExternalAnnotator;
import com.intellij.lang.annotation.HighlightSeverity;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
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
import java.util.concurrent.CompletableFuture;
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
        CompletableFuture<SemanticTokens> semanticTokens = connection.getSemanticTokens();
        try {
            return Pair.create(semanticTokens.get(2, TimeUnit.SECONDS), connection);
        } catch (Exception e) {
            LOG.error("Unable to compute semantic tokens.", e);
            return null;
        }
    }

    @Override
    public void apply(@NotNull PsiFile file, Pair<SemanticTokens, EditorLanguageServerConnection> pair, @NotNull AnnotationHolder holder) {
        ILSPEditor editor = pair.second.getEditor();
        if (editor == null) {
            return;
        }

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

            AnnotationBuilder range = holder.newSilentAnnotation(HighlightSeverity.INFORMATION).range(new TextRange(startOffset, endOffset));
            range.textAttributes(RobotFrameworkSyntaxHighlightingFactory.getFromType(tokenTypes.get(tokenType))).create();
        }
    }
}
