package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.editor.event.DocumentListener;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.UserDataHolder;
import com.intellij.openapi.util.text.StringUtil;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class EditorLanguageServerConnection {
    private static final Logger LOG = Logger.getInstance(LanguageServerCommunication.class);

    private final static Key<Object> KEY_IN_USER_DATA = Key.create(EditorLanguageServerConnection.class.getName());

    private final LanguageServerManager languageServerManager;
    private final ILSPEditor editor;
    private final TextDocumentIdentifier identifier;
    private final DocumentListener documentListener;
    private final String projectRoot;
    private final LanguageServerCommunication.IDiagnosticsListener diagnosticsListener;

    private final AtomicInteger version = new AtomicInteger(-1);
    private SemanticTokensWithRegistrationOptions semanticTokensProvider;

    private EditorLanguageServerConnection(LanguageServerManager manager, ILSPEditor editor) throws ExecutionException, InterruptedException, LanguageServerUnavailableException, TimeoutException, IOException {
        this.languageServerManager = manager;
        this.editor = editor;
        this.projectRoot = editor.getProjectPath();
        this.identifier = new TextDocumentIdentifier(editor.getURI());

        LanguageServerCommunication comm = editor.getLanguageServerCommunication(manager);
        if (comm == null) {
            throw new LanguageServerUnavailableException("Unable to get language server communication for:\n" +
                    "URI: " + editor.getURI() + "\n" +
                    "Language definition: " + editor.getLanguageDefinition() + "\n" +
                    "Project root: " + projectRoot + "\n"
            );
        }

        diagnosticsListener = params -> {
            List<Diagnostic> diagnostics = params.getDiagnostics();
            editor.setDiagnostics(diagnostics);
        };
        comm.addDiagnosticsListener(editor.getURI(), diagnosticsListener);
        comm.didOpen(this);

        ServerCapabilities serverCapabilities = comm.getServerCapabilities();
        if (serverCapabilities == null) {
            throw new LanguageServerUnavailableException("Unable to get language server capabilities for: " + projectRoot);
        }
        semanticTokensProvider = serverCapabilities.getSemanticTokensProvider();

        documentListener = new DocumentListener() {
            private boolean doFullSync = true;

            @Override
            public void documentChanged(@NotNull DocumentEvent event) {

                try {
                    LanguageServerDefinition languageDefinition = editor.getLanguageDefinition();
                    if (languageDefinition == null) {
                        return;
                    }
                    LanguageServerCommunication comm = editor.getLanguageServerCommunication(manager);
                    if (comm == null) {
                        return;
                    }
                    TextDocumentContentChangeEvent changeEvent = new TextDocumentContentChangeEvent();
                    DidChangeTextDocumentParams changesParams = createChangesParams(changeEvent);

                    if (doFullSync) {
                        changeEvent.setText(editor.getText());
                    } else {
                        TextDocumentSyncKind syncKind;
                        try {
                            syncKind = comm.getServerCapabilitySyncKind();
                        } catch (LanguageServerUnavailableException e) {
                            // If it's not available, just bail out.
                            return;
                        }

                        if (syncKind == TextDocumentSyncKind.Incremental) {
                            CharSequence newText = event.getNewFragment();
                            int offset = event.getOffset();
                            int newTextLength = event.getNewLength();
                            Position lspPosition = editor.offsetToLSPPos(offset);
                            int startLine = lspPosition.getLine();
                            int startColumn = lspPosition.getCharacter();
                            CharSequence oldText = event.getOldFragment();

                            //if text was deleted/replaced, calculate the end position of inserted/deleted text
                            int endLine, endColumn;
                            if (oldText.length() > 0) {
                                endLine = startLine + StringUtil.countNewLines(oldText);
                                String content = oldText.toString();
                                String[] oldLines = content.split("\n");
                                int oldTextLength = oldLines.length == 0 ? 0 : oldLines[oldLines.length - 1].length();
                                endColumn = content.endsWith("\n") ? 0 : oldLines.length == 1 ? startColumn + oldTextLength : oldTextLength;
                            } else { //if insert or no text change, the end position is the same
                                endLine = startLine;
                                endColumn = startColumn;
                            }
                            Range range = new Range(new Position(startLine, startColumn), new Position(endLine, endColumn));
                            changeEvent.setRange(range);
                            changeEvent.setRangeLength(newTextLength);
                            changeEvent.setText(newText.toString());
                        } else if (syncKind == TextDocumentSyncKind.Full) {
                            changeEvent.setText(editor.getText());
                        }
                    }
                    doFullSync = false;
                    comm.didChange(changesParams);
                } catch (ProcessCanceledException | CompletionException | CancellationException | InterruptedException | TimeoutException e) {
                    // If it was cancelled, just ignore it (don't log).
                    doFullSync = true; // Next time we'll have to do a full sync!
                    LOG.error("When sending document changes to the language server a message timed out (a full document sync will be done on the next change).", e);
                } catch (Exception e) {
                    doFullSync = true; // Next time we'll have to do a full sync!
                    LOG.error("When sending document changes to the language server an error occurred (a full document sync will be done on the next change).", e);
                }
            }

            @NotNull
            private DidChangeTextDocumentParams createChangesParams(TextDocumentContentChangeEvent changeEvent) {
                DidChangeTextDocumentParams changesParams = new DidChangeTextDocumentParams(new VersionedTextDocumentIdentifier(),
                        Collections.singletonList(changeEvent));
                changesParams.getTextDocument().setUri(identifier.getUri());
                changesParams.getTextDocument().setVersion(version.incrementAndGet());
                return changesParams;
            }
        };
        Document document = editor.getDocument();
        document.addDocumentListener(documentListener);
    }

    @Nullable
    public DidOpenTextDocumentParams getDidOpenTextDocumentParams() {
        LanguageServerDefinition languageDefinition = editor.getLanguageDefinition();
        if (languageDefinition == null) {
            return null;
        }
        String languageId = languageDefinition.getLanguageId();
        TextDocumentItem textDocumentItem = new TextDocumentItem(identifier.getUri(), languageId, version.incrementAndGet(), editor.getText());
        return new DidOpenTextDocumentParams(textDocumentItem);
    }

    public static void editorCreated(LanguageServerManager manager, ILSPEditor editor) throws ExecutionException, InterruptedException, LanguageServerUnavailableException, TimeoutException, IOException {
        EditorLanguageServerConnection conn = new EditorLanguageServerConnection(manager, editor);
        // i.e.: notifies of open and start listening for document changes.
        editor.putUserData(KEY_IN_USER_DATA, conn);
    }

    public static EditorLanguageServerConnection getFromUserData(UserDataHolder editor) {
        @Nullable Object data = editor.getUserData(KEY_IN_USER_DATA);
        if (data instanceof EditorLanguageServerConnection) {
            return (EditorLanguageServerConnection) data;
        }
        return null;
    }

    public ILSPEditor getEditor() {
        return editor;
    }

    public void editorReleased() throws InterruptedException, ExecutionException, TimeoutException, IOException {
        Object userData = editor.getUserData(KEY_IN_USER_DATA);
        if (userData == null) {
            return;
        }
        if (userData == this) {
            // I.e.: closes the connection.
            LanguageServerDefinition languageDefinition = editor.getLanguageDefinition();
            if (languageDefinition != null) {
                LanguageServerCommunication comm = editor.getLanguageServerCommunication(languageServerManager);
                if (comm != null) {
                    comm.didClose(this);
                    comm.removeDiagnosticsListener(editor.getURI(), diagnosticsListener);
                }
            }
            editor.getDocument().removeDocumentListener(documentListener);
            editor.putUserData(KEY_IN_USER_DATA, null);
        } else {
            LOG.info("editorReleased called for wrong EditorLanguageServerConnection?");
        }
    }

    public TextDocumentIdentifier getIdentifier() {
        return identifier;
    }

    public @NotNull List<Diagnostic> getDiagnostics() {
        return editor.getDiagnostics();
    }

    /**
     * Note: return of a negative number means the position is no longer valid.
     */
    public int LSPPosToOffset(Position pos) {
        return editor.LSPPosToOffset(pos);
    }

    public @Nullable CompletableFuture<Either<List<CompletionItem>, CompletionList>> completion(int offset) {
        try {
            LanguageServerCommunication comm = editor.getLanguageServerCommunication(languageServerManager);
            if (comm == null) {
                return null;
            }
            Position pos = editor.offsetToLSPPos(offset);
            CompletionParams params = new CompletionParams(identifier, pos);
            @Nullable CompletableFuture<Either<List<CompletionItem>, CompletionList>> completion = comm.completion(params);
            // May be null
            return completion;
        } catch (ProcessCanceledException | CompletionException | CancellationException | InterruptedException | TimeoutException e) {
            // If it was cancelled, just ignore it (don't log).
        } catch (Exception e) {
            LOG.error(e);
        }
        return null;
    }

    public @Nullable ServerCapabilities getServerCapabilities() {
        try {
            LanguageServerCommunication comm = editor.getLanguageServerCommunication(languageServerManager);
            if (comm == null) {
                return null;
            }
            return comm.getServerCapabilities();
        } catch (ProcessCanceledException | CompletionException | CancellationException | InterruptedException | TimeoutException e) {
            // If it was cancelled, just ignore it (don't log).
        } catch (Exception e) {
            LOG.error(e);
        }
        return null;
    }

    public @Nullable LanguageServerCommunication getLanguageServerCommunication() {
        try {
            LanguageServerDefinition languageDefinition = editor.getLanguageDefinition();
            if (languageDefinition != null) {
                return editor.getLanguageServerCommunication(languageServerManager);
            }
        } catch (ProcessCanceledException | CompletionException | CancellationException | InterruptedException | TimeoutException e) {
            // If it was cancelled, just ignore it (don't log).
        } catch (Exception e) {
            LOG.error(e);
        }
        return null;
    }

    public SemanticTokensWithRegistrationOptions getSemanticTokensProvider() {
        return semanticTokensProvider;
    }

    public CompletableFuture<SemanticTokens> getSemanticTokens() {
        try {
            LanguageServerCommunication comm = getLanguageServerCommunication();
            if (comm == null) {
                return null;
            }
            SemanticTokensParams params = new SemanticTokensParams(identifier);
            return comm.getSemanticTokens(params);
        } catch (ProcessCanceledException | CompletionException | CancellationException e) {
            // If it was cancelled, just ignore it (don't log).
        } catch (Exception e) {
            LOG.error(e);
        }
        return null;
    }
}
