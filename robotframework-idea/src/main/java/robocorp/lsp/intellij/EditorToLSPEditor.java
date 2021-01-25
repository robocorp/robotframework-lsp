package robocorp.lsp.intellij;

import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.UserDataHolderBase;
import com.intellij.openapi.vfs.VirtualFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.lang.ref.WeakReference;
import java.util.Map;

class EditorAsLSPEditor implements ILSPEditor {

    private final WeakReference<Editor> editor;
    private final LanguageServerDefinition definition;
    private final String uri;
    private final String extension;
    private final String projectPath;

    public EditorAsLSPEditor(Editor editor) {
        this.editor = new WeakReference<>(editor);
        VirtualFile file = EditorUtils.getVirtualFile(editor);
        if (file == null) {
            definition = null;
            uri = null;
            extension = null;
            projectPath = null;
            return;
        }
        definition = EditorUtils.getLanguageDefinition(file);
        uri = Uris.toUri(file);
        extension = "." + file.getExtension();
        Project project = editor.getProject();
        if (project != null) {
            projectPath = project.getBasePath();
        } else {
            projectPath = null;
        }
    }

    @Override
    public @Nullable LanguageServerDefinition getLanguageDefinition() {
        return definition;
    }

    @Override
    public @Nullable String getURI() {
        return uri;
    }

    @Override
    public @Nullable String getExtension() {
        return extension;
    }

    @Override
    public @Nullable String getProjectPath() {
        return projectPath;
    }

    @Override
    public <T> @Nullable T getUserData(@NotNull Key<T> key) {
        Editor editor = this.editor.get();
        if (editor == null) {
            return null;
        }
        return editor.getUserData(key);
    }

    @Override
    public <T> void putUserData(@NotNull Key<T> key, @Nullable T value) {
        Editor editor = this.editor.get();
        if (editor == null) {
            return;
        }
        editor.putUserData(key, value);
    }
}

class LSPEditorStub extends UserDataHolderBase implements ILSPEditor {

    private final LanguageServerDefinition definition;
    private final String uri;
    private final String extension;
    private final String projectPath;

    public LSPEditorStub(LanguageServerDefinition definition, String uri, String extension, String projectPath) {
        this.definition = definition;
        this.uri = uri;
        this.extension = extension;
        this.projectPath = projectPath;
    }

    @Override
    public @Nullable LanguageServerDefinition getLanguageDefinition() {
        return definition;
    }

    @Override
    public @Nullable String getURI() {
        return uri;
    }

    @Override
    public @Nullable String getExtension() {
        return extension;
    }

    @Override
    public @Nullable String getProjectPath() {
        return projectPath;
    }
}

public class EditorToLSPEditor {
    public static ILSPEditor wrap(Editor editor) {
        return new EditorAsLSPEditor(editor);
    }

    public static ILSPEditor createStub(LanguageServerDefinition definition, String uri, String extension, String projectPath) {
        return new LSPEditorStub(definition, uri, extension, projectPath);
    }
}
