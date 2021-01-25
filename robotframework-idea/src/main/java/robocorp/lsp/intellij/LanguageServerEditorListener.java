package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.event.EditorFactoryEvent;
import com.intellij.openapi.editor.event.EditorFactoryListener;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import org.jetbrains.annotations.NotNull;

import java.io.IOException;

public class LanguageServerEditorListener implements EditorFactoryListener {
    private static final Logger LOG = Logger.getInstance(LanguageServerEditorListener.class);

    public void editorCreated(@NotNull EditorFactoryEvent event) {
        Editor editor = event.getEditor();
        VirtualFile file = EditorUtils.getVirtualFile(editor);
        if (file == null) {
            return;
        }
        LanguageServerDefinition definition = EditorUtils.getLanguageDefinition(file);
        if (definition == null) {
            return;
        }
        String uri = Uris.toUri(file);
        Project project = editor.getProject();
        try {
            LanguageServerManager manager = LanguageServerManager.start(definition, "." + file.getExtension(), project.getBasePath());
            EditorLanguageServerConnection.setup(manager, editor);
        } catch (IOException e) {
            LOG.error(e);
        }
    }
}
