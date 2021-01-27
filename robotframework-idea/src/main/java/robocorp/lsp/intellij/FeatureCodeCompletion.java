package robocorp.lsp.intellij;

import com.intellij.codeInsight.completion.CompletionContributor;
import com.intellij.codeInsight.completion.CompletionParameters;
import com.intellij.codeInsight.completion.CompletionResultSet;
import com.intellij.codeInsight.completion.InsertionContext;
import com.intellij.codeInsight.lookup.LookupElement;
import com.intellij.codeInsight.lookup.LookupElementPresentation;
import com.intellij.openapi.application.ex.ApplicationUtil;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.progress.ProgressIndicatorProvider;
import com.intellij.openapi.util.text.StringUtil;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.jetbrains.annotations.NotNull;

import javax.swing.*;
import javax.swing.text.BadLocationException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

public class FeatureCodeCompletion extends CompletionContributor {
    private static final Logger LOG = Logger.getInstance(FeatureCodeCompletion.class);

    @Override
    public void fillCompletionVariants(@NotNull CompletionParameters parameters, @NotNull CompletionResultSet result) {
        final Editor editor = parameters.getEditor();
        final int offset = parameters.getOffset();
        final EditorLanguageServerConnection editorLanguageServerConnection = EditorLanguageServerConnection.getFromUserData(editor);
        if (editorLanguageServerConnection != null) {
            try {
                ApplicationUtil.runWithCheckCanceled(() -> {
                    CompletableFuture<Either<List<CompletionItem>, CompletionList>> completion = editorLanguageServerConnection.completion(offset);
                    if (completion == null) {
                        return null;
                    }
                    Either<List<CompletionItem>, CompletionList> res = completion.get(5, TimeUnit.SECONDS);
                    if (res == null) {
                        return null;
                    }

                    result.startBatch();
                    try {
                        if (res.getLeft() != null) {
                            for (CompletionItem item : res.getLeft()) {
                                LookupElement lookupElement = createLookupItem(item);
                                if (lookupElement != null) {
                                    result.addElement(lookupElement);
                                }
                            }
                        } else if (res.getRight() != null) {
                            for (CompletionItem item : res.getRight().getItems()) {
                                LookupElement lookupElement = createLookupItem(item);
                                if (lookupElement != null) {
                                    result.addElement(lookupElement);
                                }
                            }
                        }
                    } finally {
                        result.endBatch();
                    }

                    return null;
                }, ProgressIndicatorProvider.getGlobalProgressIndicator());
            } catch (ProcessCanceledException ignored) {
                // Cancelled.
            } catch (Exception e) {
                LOG.error("Unable to get completions", e);
            }
        }
    }

    private LookupElement createLookupItem(final CompletionItem item) {
        final CompletionItemKind kind = item.getKind();
        final String label = item.getLabel();
        final Icon icon = LanguageServerIcons.getCompletionIcon(kind);

        return new LookupElement() {

            @Override
            public @NotNull String getLookupString() {
                return label;
            }

            @Override
            public boolean requiresCommittedDocuments() {
                return false;
            }

            @Override
            public void renderElement(LookupElementPresentation presentation) {
                presentation.setItemText(label);
                presentation.setItemTextBold(kind == CompletionItemKind.Keyword);
                presentation.setIcon(icon);
            }

            @Override
            public boolean isCaseSensitive() {
                return false;
            }

            @Override
            public void handleInsert(@NotNull InsertionContext context) {
                Document document = context.getDocument();
                document.deleteString(context.getStartOffset(), context.getTailOffset());

                ArrayList<TextEdit> lst = new ArrayList<>();
                TextEdit textEdit = item.getTextEdit();
                lst.add(textEdit);
                List<TextEdit> additionalTextEdits = item.getAdditionalTextEdits();
                if (additionalTextEdits != null) {
                    lst.addAll(additionalTextEdits);
                }
                try {
                    EditorUtils.applyTextEdits(document, lst);
                    context.commitDocument();
                } catch (BadLocationException e) {
                    LOG.error(e);
                }

                // Calculate the new cursor offset.
                Position startPos = textEdit.getRange().getStart();
                Position offsetPos = new Position(startPos.getLine(), startPos.getCharacter());
                if (additionalTextEdits != null) {
                    for (TextEdit t : additionalTextEdits) {
                        if (t.getRange().getStart().getLine() < offsetPos.getLine()) {
                            int newLines = StringUtil.countNewLines(t.getNewText());
                            offsetPos.setLine(offsetPos.getLine() + newLines);
                        }
                    }
                }
                int offset = EditorUtils.LSPPosToOffset(document, offsetPos) + textEdit.getNewText().length();
                context.getEditor().getCaretModel().moveToOffset(offset);
            }
        };
    }

}
