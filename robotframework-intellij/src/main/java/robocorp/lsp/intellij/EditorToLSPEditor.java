package robocorp.lsp.intellij;

import com.intellij.codeInsight.daemon.DaemonCodeAnalyzer;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiDocumentManager;
import com.intellij.psi.PsiFile;
import org.eclipse.lsp4j.Diagnostic;
import org.eclipse.lsp4j.Position;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.robot.intellij.CancelledException;

import java.io.IOException;
import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeoutException;

public class EditorToLSPEditor {
    private static final Logger LOG = Logger.getInstance(EditorToLSPEditor.class);

    public static class EditorAsLSPEditor implements ILSPEditor {

        private final WeakReference<Editor> editor;
        private final LanguageServerDefinition definition;
        private final String uri;
        private final String extensionForLanguageServerQuery;
        private final String projectPath;
        private volatile List<Diagnostic> diagnostics = new ArrayList<>();

        public EditorAsLSPEditor(Editor editor) throws CancelledException {
            this.editor = new WeakReference<>(editor);
            VirtualFile file = EditorUtils.getVirtualFile(editor);
            if (file == null) {
                definition = null;
                uri = null;
                extensionForLanguageServerQuery = null;
                projectPath = null;
                return;
            }
            uri = Uris.toUri(file);
            @Nullable Project project = editor.getProject();

            // loads to project
            if (project != null) {
                definition = EditorUtils.getLanguageDefinition(file, project);
                if (definition != null) {
                    extensionForLanguageServerQuery = definition.ext.iterator().next();
                    projectPath = project.getBasePath();
                } else {
                    extensionForLanguageServerQuery = null;
                    projectPath = null;
                }
            } else {
                extensionForLanguageServerQuery = null;
                definition = null;
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
        public @Nullable String getProjectPath() {
            return projectPath;
        }

        @Nullable
        @Override
        public Project getProject() {
            Editor editor = this.editor.get();
            if (editor == null) {
                throw new RuntimeException("Editor already disposed.");
            }
            return editor.getProject();
        }

        @Override
        public Position offsetToLSPPos(int offset) {
            Editor editor = this.editor.get();
            if (editor == null) {
                throw new RuntimeException("Editor already disposed.");
            }
            return EditorUtils.offsetToLSPPos(editor, offset);
        }

        @Override
        public int LSPPosToOffset(Position pos) {
            Editor editor = this.editor.get();
            if (editor == null) {
                throw new RuntimeException("Editor already disposed.");
            }
            return EditorUtils.LSPPosToOffset(editor, pos);
        }

        @Override
        public String getText() {
            Editor editor = this.editor.get();
            if (editor == null) {
                throw new RuntimeException("Editor already disposed.");
            }
            return editor.getDocument().getText();
        }

        @Override
        public Document getDocument() {
            Editor editor = this.editor.get();
            if (editor == null) {
                throw new RuntimeException("Editor already disposed.");
            }
            return editor.getDocument();
        }

        @Override
        public void setDiagnostics(@NotNull List<Diagnostic> diagnostics) {
            this.diagnostics = Collections.unmodifiableList(diagnostics);
            ApplicationManager.getApplication().invokeLater(() -> {
                Editor editor = this.editor.get();
                if (editor == null || editor.isDisposed()) {
                    return;
                }
                Project project = editor.getProject();
                final PsiFile file = PsiDocumentManager.getInstance(project).getCachedPsiFile(editor.getDocument());
                if (file == null) {
                    return;
                }
                LOG.debug("Triggering force full DaemonCodeAnalyzer execution.");
                DaemonCodeAnalyzer.getInstance(project).restart(file);
            });
        }

        @Override
        public @NotNull List<Diagnostic> getDiagnostics() {
            return diagnostics;
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

        @Override
        public LanguageServerCommunication getLanguageServerCommunication(LanguageServerManager languageServerManager) throws InterruptedException, ExecutionException, TimeoutException, IOException {
            if (definition == null || extensionForLanguageServerQuery == null) {
                return null;
            }
            @Nullable Project project = getProject();
            LanguageServerCommunication comm = languageServerManager.getLanguageServerCommunication(extensionForLanguageServerQuery, getProjectPath(), project);
            return comm;
        }
    }

    public static ILSPEditor wrap(Editor editor) throws CancelledException {
        return new EditorAsLSPEditor(editor);
    }

}
