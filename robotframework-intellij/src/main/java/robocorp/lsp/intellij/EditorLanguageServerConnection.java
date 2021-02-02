package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.editor.event.DocumentListener;
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
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeoutException;

public class EditorLanguageServerConnection {
    private static final Logger LOG = Logger.getInstance(LanguageServerCommunication.class);

    private final static Key<Object> KEY_IN_USER_DATA = Key.create(EditorLanguageServerConnection.class.getName());

    private final LanguageServerManager languageServerManager;
    private final ILSPEditor editor;
    private final TextDocumentIdentifier identifier;
    private final DocumentListener documentListener;
    private final String projectRoot;
    private final TextDocumentSyncKind syncKind;
    private final LanguageServerCommunication.IDiagnosticsListener diagnosticsListener;

    private volatile int version = -1;

    private EditorLanguageServerConnection(LanguageServerManager manager, ILSPEditor editor) throws ExecutionException, InterruptedException, LanguageServerUnavailableException, TimeoutException, IOException {
        this.languageServerManager = manager;
        this.editor = editor;
        this.projectRoot = editor.getProjectPath();
        this.identifier = new TextDocumentIdentifier(editor.getURI());

        LanguageServerCommunication comm = manager.getLanguageServerCommunication(editor.getExtension(), projectRoot);
        if (comm == null) {
            throw new LanguageServerUnavailableException("Unable to get language server communication for: " + projectRoot);
        }
        diagnosticsListener = params -> {
            List<Diagnostic> diagnostics = params.getDiagnostics();
            editor.setDiagnostics(diagnostics);
        };
        comm.addDiagnosticsListener(editor.getURI(), diagnosticsListener);
        this.syncKind = comm.getServerCapabilitySyncKind();

        String languageId = editor.getLanguageDefinition().getLanguageId();
        version += 1;
        comm.didOpen(new DidOpenTextDocumentParams(new TextDocumentItem(identifier.getUri(), languageId, version, editor.getText())));

        documentListener = new DocumentListener() {
            @Override
            public void documentChanged(@NotNull DocumentEvent event) {
                TextDocumentContentChangeEvent changeEvent = new TextDocumentContentChangeEvent();
                DidChangeTextDocumentParams changesParams = new DidChangeTextDocumentParams(new VersionedTextDocumentIdentifier(),
                        Collections.singletonList(changeEvent));
                changesParams.getTextDocument().setUri(identifier.getUri());
                version += 1;
                changesParams.getTextDocument().setVersion(version);

                try {
                    LanguageServerCommunication comm = manager.getLanguageServerCommunication(editor.getExtension(), projectRoot);

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
                    comm.didChange(changesParams);
                } catch (Exception e) {
                    LOG.error(e);
                }
            }
        };
        Document document = editor.getDocument();
        document.addDocumentListener(documentListener);
    }

    public static EditorLanguageServerConnection editorCreated(LanguageServerManager manager, ILSPEditor editor) throws ExecutionException, InterruptedException, LanguageServerUnavailableException, TimeoutException, IOException {
        EditorLanguageServerConnection conn = new EditorLanguageServerConnection(manager, editor);
        // i.e.: notifies of open and start listening for document changes.
        editor.putUserData(KEY_IN_USER_DATA, conn);
        return conn;
    }

    public static EditorLanguageServerConnection getFromUserData(UserDataHolder editor) {
        @Nullable Object data = editor.getUserData(KEY_IN_USER_DATA);
        if (data instanceof EditorLanguageServerConnection) {
            return (EditorLanguageServerConnection) data;
        }
        return null;
    }

    public void editorReleased() throws InterruptedException, ExecutionException, TimeoutException, IOException {
        Object userData = editor.getUserData(KEY_IN_USER_DATA);
        if (userData == null) {
            return;
        }
        if (userData == this) {
            // I.e.: closes the connection.
            LanguageServerCommunication comm = languageServerManager.getLanguageServerCommunication(editor.getExtension(), projectRoot);
            comm.didClose(new DidCloseTextDocumentParams(identifier));
            comm.removeDiagnosticsListener(editor.getURI(), diagnosticsListener);

            editor.getDocument().removeDocumentListener(documentListener);
            editor.putUserData(KEY_IN_USER_DATA, null);
        } else {
            LOG.info("editorReleased called for wrong EditorLanguageServerConnection?");
        }
    }

    public String getURI() {
        return editor.getURI();
    }

    public @NotNull List<Diagnostic> getDiagnostics() {
        return editor.getDiagnostics();
    }

    public int LSPPosToOffset(Position pos) {
        return editor.LSPPosToOffset(pos);
    }

    public @Nullable CompletableFuture<Either<List<CompletionItem>, CompletionList>> completion(int offset) {
        try {
            LanguageServerCommunication comm = languageServerManager.getLanguageServerCommunication(editor.getExtension(), projectRoot);
            Position pos = editor.offsetToLSPPos(offset);
            CompletionParams params = new CompletionParams(identifier, pos);
            CompletableFuture<Either<List<CompletionItem>, CompletionList>> completion = comm.completion(params);
            return completion;
        } catch (Exception e) {
            LOG.error(e);
        }
        return null;
    }

    public @Nullable ServerCapabilities getServerCapabilities() {
        try {
            LanguageServerCommunication comm = languageServerManager.getLanguageServerCommunication(editor.getExtension(), projectRoot);
            return comm.getServerCapabilities();
        } catch (Exception e) {
            LOG.error(e);
        }
        return null;
    }
}
