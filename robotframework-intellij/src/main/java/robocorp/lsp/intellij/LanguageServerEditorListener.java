package robocorp.lsp.intellij;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.event.EditorFactoryEvent;
import com.intellij.openapi.editor.event.EditorFactoryListener;
import com.intellij.openapi.project.Project;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.robot.intellij.CancelledException;

public class LanguageServerEditorListener implements EditorFactoryListener {
    private static final Logger LOG = Logger.getInstance(LanguageServerEditorListener.class);

    public LanguageServerEditorListener() {
        LOG.debug("Created LanguageServerEditorListener");
    }

    @Override
    public void editorCreated(@NotNull EditorFactoryEvent event) {
        Editor editor = event.getEditor();

        try {
            editorCreated(EditorToLSPEditor.wrap(editor));
            return;
        } catch (CancelledException e) {
            // If it was cancelled try it (once) later on...
        }

        ApplicationManager.getApplication().invokeLater(() -> {
            try {
                editorCreated(EditorToLSPEditor.wrap(editor));
            } catch (CancelledException e) {
                LOG.info("Cancelled (in invokeLater) creating an EditorToLSPEditor connection.");
            }
        });
    }

    @Override
    public void editorReleased(@NotNull EditorFactoryEvent event) {
        Editor editor = event.getEditor();
        EditorLanguageServerConnection conn = EditorLanguageServerConnection.getFromUserData(editor);
        if (conn != null) {
            try {
                conn.editorReleased();
            } catch (Exception e) {
                LOG.error(e);
            }
        }
    }

    public void editorCreated(ILSPEditor editor) {
        @Nullable LanguageServerDefinition definition = editor.getLanguageDefinition();
        if (definition == null) {
            return;
        }

        String uri = editor.getURI();
        String projectPath = editor.getProjectPath();
        Project project = editor.getProject();
        if (uri == null || projectPath == null || project == null) {
            return;
        }

        try {
            LanguageServerManager manager = LanguageServerManager.start(definition, definition.ext.iterator().next(), projectPath, project);
            EditorLanguageServerConnection.editorCreated(manager, editor);
        } catch (Exception e) {
            LOG.error(e);
        }
    }
}
