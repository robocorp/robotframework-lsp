package robocorp.lsp.intellij;

import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.editor.event.DocumentListener;
import com.intellij.openapi.util.Key;
import org.eclipse.lsp4j.DidChangeTextDocumentParams;
import org.eclipse.lsp4j.TextDocumentContentChangeEvent;
import org.eclipse.lsp4j.TextDocumentIdentifier;
import org.eclipse.lsp4j.VersionedTextDocumentIdentifier;
import org.jetbrains.annotations.NotNull;

import java.lang.ref.WeakReference;
import java.util.Collections;

public class EditorLanguageServerConnection {
    private final LanguageServerManager languageServerManager;
    private final ILSPEditor editor;
    private final TextDocumentIdentifier identifier;
    private final DocumentListener documentListener;
    private final String projectRoot;
    private int version = -1;

    private EditorLanguageServerConnection(LanguageServerManager manager, ILSPEditor editor) {
        this.languageServerManager = manager;
        this.editor = editor;
        this.projectRoot = editor.getProjectPath();
        this.identifier = new TextDocumentIdentifier(editor.getURI());
        documentListener = new DocumentListener() {
            @Override
            public void documentChanged(@NotNull DocumentEvent event) {
                DidChangeTextDocumentParams changesParams = new DidChangeTextDocumentParams(new VersionedTextDocumentIdentifier(),
                        Collections.singletonList(new TextDocumentContentChangeEvent()));
                changesParams.getTextDocument().setUri(identifier.getUri());
                changesParams.getTextDocument().setVersion(version++);

            }
        };
    }

    public static void setup(LanguageServerManager manager, ILSPEditor editor) {
        EditorLanguageServerConnection conn = new EditorLanguageServerConnection(manager, editor);
        editor.putUserData(Key.create(EditorLanguageServerConnection.class.getName()), conn);
    }
}
