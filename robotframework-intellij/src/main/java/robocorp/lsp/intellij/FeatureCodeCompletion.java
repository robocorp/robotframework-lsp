/*
 * Original work Copyright (c) 2019, WSO2 Inc. (http://www.wso2.org) (Apache 2.0)
 * See ThirdPartyNotices.txt in the project root for license information.
 * All modifications Copyright (c) Robocorp Technologies Inc.
 * All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License")
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http: // www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package robocorp.lsp.intellij;

import com.intellij.codeInsight.completion.*;
import com.intellij.codeInsight.lookup.LookupElement;
import com.intellij.codeInsight.lookup.LookupElementPresentation;
import com.intellij.codeInsight.template.TemplateManager;
import com.intellij.codeInsight.template.impl.TemplateImpl;
import com.intellij.codeInsight.template.impl.TextExpression;
import com.intellij.openapi.application.ex.ApplicationUtil;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.EditorModificationUtil;
import com.intellij.openapi.progress.EmptyProgressIndicator;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressIndicatorProvider;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.text.StringUtil;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.jetbrains.annotations.NotNull;

import javax.swing.*;
import javax.swing.text.BadLocationException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

// https://intellij-support.jetbrains.com/hc/en-us/community/posts/360010327299-Code-completion-without-applying-initial-lookupString
// (Code-completion without applying initial lookupString)
public class FeatureCodeCompletion extends CompletionContributor {
    private static final Logger LOG = Logger.getInstance(FeatureCodeCompletion.class);

    private static class SnippetVariable {
        String lspSnippetText;
        int startIndex;
        int endIndex;
        String variableValue;

        SnippetVariable(String text, int start, int end) {
            this.lspSnippetText = text;
            this.startIndex = start;
            this.endIndex = end;
            this.variableValue = getVariableValue(text);
        }

        private String getVariableValue(String lspVarSnippet) {
            if (lspVarSnippet.contains(":")) {
                return lspVarSnippet.substring(lspVarSnippet.indexOf(':') + 1, lspVarSnippet.lastIndexOf('}'));
            }
            return " ";
        }
    }

    public static class LSPPrefixMatcher extends PrefixMatcher {

        private final String normalizedPrefix;

        public static String getPrefix(String lineToCursor) {
            // This is really unfortunate. We have to add logic which should be in the language
            // server in the client as it seems there's no way to not have Intellij use that
            // info (even if doing so makes things wrong).
            // This is used both when applying a completion and even when Intellij tries
            // to be smart and applies a partial completion just based on the prefix
            // (i.e.: https://github.com/robocorp/robotframework-lsp/issues/248)
            // The logic below is only valid for the Robot Framework Language Server (other
            // language servers would need to have a custom logic here).
            FastStringBuffer buf = new FastStringBuffer(lineToCursor, 0);
            if (buf.length() == 0) {
                return "";
            }
            StringBuilder builder = new StringBuilder();
            if (buf.lastChar() == ' ') {
                buf.deleteLast();
                builder.append(' ');
            }
            // 2 spaces
            if (buf.lastChar() == ' ') {
                return "";
            }

            while (buf.length() > 0) {
                char c = buf.lastChar();
                buf.deleteLast();

                if (c == ' ' && (buf.length() == 0 || buf.lastChar() == ' ' || buf.lastChar() == '}')) {
                    // 2 spaces or a single space before the line end.
                    return builder.reverse().toString();
                }

                if (c == '.' || c == '/') {
                    return builder.reverse().toString();
                }
                builder.append(c);
                if (c == '{' && !buf.isEmpty()) {
                    char last = buf.lastChar();
                    if (last == '$' || last == '@' || last == '&') {
                        builder.append(last);
                        return builder.reverse().toString();
                    }
                }
            }
            if (builder.length() > 0) {
                return builder.reverse().toString();
            }
            return lineToCursor;
        }

        public LSPPrefixMatcher(String lineToCursor) {
            super(getPrefix(lineToCursor));
            normalizedPrefix = normalizeRobotName(myPrefix);
        }

        private static String normalizeRobotName(String myPrefix) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < myPrefix.length(); i++) {
                char c = myPrefix.charAt(i);
                if (!Character.isWhitespace(c) && c != '_') {
                    sb.append(Character.toLowerCase(c));
                }
            }
            return sb.toString();
        }

        @Override
        public boolean prefixMatches(@NotNull String name) {
            name = normalizeRobotName(name);
            return name.contains(normalizedPrefix);
        }

        @Override
        public @NotNull PrefixMatcher cloneWithPrefix(@NotNull String prefix) {
            return new LSPPrefixMatcher(prefix);
        }
    }

    @Override
    public void fillCompletionVariants(@NotNull CompletionParameters parameters, @NotNull CompletionResultSet result) {
        final Editor editor = parameters.getEditor();
        final int offset = parameters.getOffset();
        final EditorLanguageServerConnection editorLanguageServerConnection = EditorLanguageServerConnection.getFromUserData(editor);
        if (editorLanguageServerConnection != null) {
            try {
                final String lineToCursor = EditorUtils.getLineToCursor(editor.getDocument(), offset);

                ProgressIndicator progressIndicator = ProgressIndicatorProvider.getGlobalProgressIndicator();
                if (progressIndicator == null) {
                    progressIndicator = new EmptyProgressIndicator();
                }
                ApplicationUtil.runWithCheckCanceled(() -> {
                    CompletableFuture<Either<List<CompletionItem>, CompletionList>> completion = editorLanguageServerConnection.completion(offset);
                    if (completion == null) {
                        return null;
                    }
                    Either<List<CompletionItem>, CompletionList> res = completion.get(Timeouts.getCompletionTimeout(), TimeUnit.SECONDS);
                    if (res == null) {
                        return null;
                    }

                    @NotNull CompletionResultSet completionResult = result.withPrefixMatcher(new LSPPrefixMatcher(lineToCursor));

                    completionResult.startBatch();
                    try {
                        if (res.getLeft() != null) {
                            for (CompletionItem item : res.getLeft()) {
                                LookupElement lookupElement = createLookupItem(item);
                                completionResult.addElement(lookupElement);
                            }
                        } else if (res.getRight() != null) {
                            for (CompletionItem item : res.getRight().getItems()) {
                                LookupElement lookupElement = createLookupItem(item);
                                completionResult.addElement(lookupElement);
                            }
                        }
                    } finally {
                        completionResult.endBatch();
                    }

                    return null;
                }, progressIndicator);
            } catch (ProcessCanceledException ignored) {
                // Cancelled.
            } catch (Exception e) {
                LOG.error("Unable to get completions", e);
            }
        }
    }

    private @NotNull LookupElement createLookupItem(final CompletionItem item) {
        final CompletionItemKind kind = item.getKind();
        final String label = item.getLabel();
        final Icon icon = LanguageServerIcons.getCompletionIcon(kind);
        final String lookupString = label;

        return new LookupElement() {

            @Override
            public @NotNull String getLookupString() {
                return lookupString;
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
                Either<TextEdit, InsertReplaceEdit> either = item.getTextEdit();
                if (!either.isLeft()) {
                    throw new RuntimeException("Expected only TextEdit, not InsertReplaceEdit.");
                }
                TextEdit textEdit = either.getLeft();
                Document document = context.getDocument();
                int startOffset = context.getStartOffset();
                Position startPos = textEdit.getRange().getStart();
                int startPosOffset = EditorUtils.LSPPosToOffset(document, startPos);

                if (startPosOffset > startOffset) {
                    // i.e.: Don't remove what wasn't added in the first place.
                    startOffset = startPosOffset;
                }
                document.deleteString(startOffset, context.getTailOffset());

                ArrayList<TextEdit> lst = new ArrayList<>();
                final String originalText = textEdit.getNewText();
                if (item.getInsertTextFormat() == InsertTextFormat.Snippet) {
                    textEdit.setNewText(removePlaceholders(textEdit.getNewText()));
                }
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
                if (item.getInsertTextFormat() == InsertTextFormat.Snippet) {
                    prepareAndRunSnippet(context, originalText);
                }
            }

            private void prepareAndRunSnippet(@NotNull InsertionContext context, @NotNull String insertText) {
                Editor editor = context.getEditor();
                Project project = editor.getProject();
                if (project == null) {
                    return;
                }
                List<SnippetVariable> variables = new ArrayList<>();
                // Extracts variables using placeholder REGEX pattern.
                Matcher varMatcher = SNIPPET_PLACEHOLDER_REGEX.matcher(insertText);
                while (varMatcher.find()) {
                    variables.add(new SnippetVariable(varMatcher.group(), varMatcher.start(), varMatcher.end()));
                }
                if (variables.isEmpty()) {
                    return;
                }

                variables.sort(Comparator.comparingInt(o -> o.startIndex));
                final String[] finalInsertText = {insertText};
                variables.forEach(var -> finalInsertText[0] = finalInsertText[0].replace(var.lspSnippetText, "$"));

                String[] splitInsertText = finalInsertText[0].split("\\$");
                finalInsertText[0] = String.join("", splitInsertText);

                TemplateImpl template = (TemplateImpl) TemplateManager.getInstance(project).createTemplate(finalInsertText[0],
                        "groupLSP");
                template.parseSegments();

                // prevent "smart" indent of next line...
                template.setToIndent(false);

                final int[] varIndex = {0};
                variables.forEach(var -> {
                    var.variableValue = var.variableValue.replace("\\$", "$");
                    template.addTextSegment(splitInsertText[varIndex[0]]);
                    template.addVariable(varIndex[0] + "_" + var.variableValue, new TextExpression(var.variableValue),
                            new TextExpression(var.variableValue), true, false);
                    varIndex[0]++;
                });
                // If the snippet text ends with a placeholder, there will be no string segment left to append after the last
                // variable.
                if (splitInsertText.length != variables.size()) {
                    template.addTextSegment(splitInsertText[splitInsertText.length - 1]);
                }
                template.setInline(true);
                if (variables.size() > 0) {
                    EditorModificationUtil.moveCaretRelatively(editor, -template.getTemplateText().length());
                }
                TemplateManager.getInstance(project).startTemplate(editor, template);
            }
        };
    }

    public static final Pattern SNIPPET_PLACEHOLDER_REGEX = Pattern.compile("(\\$\\{\\d+:?([^{^}]*)}|\\$\\d+)");

    private String removePlaceholders(String text) {
        return SNIPPET_PLACEHOLDER_REGEX.matcher(text).replaceAll("").replace("\\$", "$");
    }

}
