package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.event.EditorFactoryEvent;
import com.intellij.openapi.editor.event.EditorFactoryListener;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;

public class LanguageServerEditorListener implements EditorFactoryListener {
    private static final Logger LOG = Logger.getInstance(LanguageServerEditorListener.class);

    public void editorCreated(@NotNull EditorFactoryEvent event) {
        Editor editor = event.getEditor();
        editorCreated(EditorToLSPEditor.wrap(editor));
    }
    public void editorCreated(ILSPEditor editor) {
        @Nullable LanguageServerDefinition definition = editor.getLanguageDefinition();
        if(definition == null){
            return;
        }

        String uri = editor.getURI();
        String projectPath = editor.getProjectPath();
        if(uri == null || projectPath == null){
            return;
        }

        try {
            LanguageServerManager manager = LanguageServerManager.start(definition, editor.getExtension(), projectPath);
            EditorLanguageServerConnection.setup(manager, editor);
        } catch (IOException e) {
            LOG.error(e);
        }
    }
}
