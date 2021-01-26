package robocorp.lsp.intellij;

import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.impl.DocumentImpl;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.UserDataHolderBase;
import com.intellij.openapi.vfs.VirtualFile;
import org.eclipse.lsp4j.Position;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.lang.ref.WeakReference;


public class EditorToLSPEditor {
    public static class EditorAsLSPEditor implements ILSPEditor {

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
        public Position offsetToLSPPos(int offset) {
            Editor editor = this.editor.get();
            if(editor == null){
                throw new RuntimeException("Editor already disposed.");
            }
            return EditorUtils.offsetToLSPPos(editor, offset);
        }

        @Override
        public String getText() {
            Editor editor = this.editor.get();
            if(editor == null){
                throw new RuntimeException("Editor already disposed.");
            }
            return editor.getDocument().getText();
        }

        @Override
        public Document getDocument() {
            Editor editor = this.editor.get();
            if(editor == null){
                throw new RuntimeException("Editor already disposed.");
            }
            return editor.getDocument();
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

    public static class LSPEditorStub extends UserDataHolderBase implements ILSPEditor {

        private final LanguageServerDefinition definition;
        private final String uri;
        private final String extension;
        private final String projectPath;
        private final DocumentImpl document;

        public LSPEditorStub(LanguageServerDefinition definition, String uri, String extension, String projectPath) {
            this.definition = definition;
            this.uri = uri;
            this.extension = extension;
            this.projectPath = projectPath;
            this.document = new DocumentImpl("");
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
        public Position offsetToLSPPos(int offset) {
            return EditorUtils.offsetToLSPPos(document, offset);
        }

        @Override
        public String getText() {
            return document.getText();
        }

        @Override
        public Document getDocument(){
            return document;
        }
    }


    public static ILSPEditor wrap(Editor editor) {
        return new EditorAsLSPEditor(editor);
    }

    public static ILSPEditor createStub(LanguageServerDefinition definition, String uri, String extension, String projectPath) {
        return new LSPEditorStub(definition, uri, extension, projectPath);
    }
}
