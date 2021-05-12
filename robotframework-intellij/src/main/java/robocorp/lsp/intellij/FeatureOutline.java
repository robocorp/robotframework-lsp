package robocorp.lsp.intellij;

import com.intellij.icons.AllIcons;
import com.intellij.ide.structureView.*;
import com.intellij.ide.util.treeView.smartTree.Sorter;
import com.intellij.ide.util.treeView.smartTree.TreeElement;
import com.intellij.lang.PsiStructureViewFactory;
import com.intellij.navigation.ItemPresentation;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.fileEditor.OpenFileDescriptor;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.NlsSafe;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiFile;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;

public class FeatureOutline implements PsiStructureViewFactory {
    private static final Logger LOG = Logger.getInstance(FeatureOutline.class);

    @Override
    public @Nullable StructureViewBuilder getStructureViewBuilder(@NotNull PsiFile psiFile) {
        return new LSPStructureViewBuilder(psiFile);
    }

    static class LSPStructureViewBuilder extends TreeBasedStructureViewBuilder {
        private final PsiFile psiFile;

        public LSPStructureViewBuilder(@NotNull PsiFile psiFile) {
            this.psiFile = psiFile;
        }

        @Override
        public @NotNull StructureViewModel createStructureViewModel(@Nullable Editor editor) {
            return new StructureViewModelBase(psiFile, editor, new RobotFileStructureViewElement(psiFile))
                    .withSorters(Sorter.ALPHA_SORTER);
        }
    }

    static class DocumentSymbolViewElement implements StructureViewTreeElement {

        private final PsiFile psiFile;
        private final DocumentSymbol documentSymbol;
        private final TreeElement[] children;

        public DocumentSymbolViewElement(PsiFile psiFile, DocumentSymbol documentSymbol) {
            this.psiFile = psiFile;
            this.documentSymbol = documentSymbol;
            List<DocumentSymbol> children = documentSymbol.getChildren();
            if (children == null) {
                this.children = TreeElement.EMPTY_ARRAY;
            } else {
                List<DocumentSymbolViewElement> temp = new ArrayList<>(children.size());
                for (DocumentSymbol child : children) {
                    temp.add(new DocumentSymbolViewElement(psiFile, child));
                }
                this.children = temp.toArray(new DocumentSymbolViewElement[0]);
            }
        }

        @Override
        public Object getValue() {
            return documentSymbol;
        }

        @Override
        public @NotNull ItemPresentation getPresentation() {
            return new ItemPresentation() {
                @Override
                public @NlsSafe @Nullable String getPresentableText() {
                    return documentSymbol.getName();
                }

                @Override
                public @NlsSafe @Nullable String getLocationString() {
                    return null;
                }

                @Override
                public @Nullable Icon getIcon(boolean unused) {
                    return LanguageServerIcons.getSymbolIcon(documentSymbol.getKind());
                }
            };
        }

        @Override
        public TreeElement @NotNull [] getChildren() {
            return children;
        }

        @Override
        public void navigate(boolean requestFocus) {
            Range selectionRange = documentSymbol.getSelectionRange();
            Position start = selectionRange.getStart();

            new OpenFileDescriptor(psiFile.getProject(), psiFile.getVirtualFile(), start.getLine(), start.getCharacter()).navigate(requestFocus);
        }

        @Override
        public boolean canNavigate() {
            return true;
        }

        @Override
        public boolean canNavigateToSource() {
            return true;
        }
    }

    static class RobotFileStructureViewElement implements StructureViewTreeElement {
        private final PsiFile psiFile;
        private TreeElement[] children;

        public RobotFileStructureViewElement(PsiFile psiFile) {
            this.psiFile = psiFile;
            this.children = TreeElement.EMPTY_ARRAY;

            @NotNull Project project = psiFile.getProject();
            VirtualFile virtualFile = psiFile.getVirtualFile();
            if (virtualFile == null || project == null) {
                return;
            }
            String basePath = project.getBasePath();
            if (basePath == null) {
                return;
            }
            LanguageServerDefinition languageDefinition = EditorUtils.getLanguageDefinition(virtualFile, project);
            if (languageDefinition == null) {
                return;
            }
            LanguageServerManager languageServerManager = LanguageServerManager.getInstance(languageDefinition);
            try {
                LanguageServerCommunication comm = languageServerManager.getLanguageServerCommunication(languageDefinition.ext.iterator().next(), basePath, project);
                if (comm == null) {
                    return;
                }
                String uri = Uris.toUri(virtualFile);

                TextDocumentIdentifier textDocumentIdentifier = new TextDocumentIdentifier(uri);
                DocumentSymbolParams params = new DocumentSymbolParams(textDocumentIdentifier);
                CompletableFuture<List<Either<SymbolInformation, DocumentSymbol>>> future = comm.documentSymbol(params);
                if (future == null) {
                    return;
                }
                List<Either<SymbolInformation, DocumentSymbol>> lst = future.get(Timeouts.getDocumentSymbolTimeout(), TimeUnit.SECONDS);
                if (lst == null) {
                    return;
                }
                List<TreeElement> temp = new ArrayList<>(lst.size());
                for (Either<SymbolInformation, DocumentSymbol> either : lst) {
                    if (either.isLeft()) {
                        SymbolInformation left = either.getLeft();
                        // Unhandled...
                    } else {
                        DocumentSymbol right = either.getRight();
                        // Handle only what we currently have...
                        temp.add(new DocumentSymbolViewElement(psiFile, right));
                    }
                }
                children = temp.toArray(new TreeElement[0]);

            } catch (ProcessCanceledException | CompletionException | CancellationException | InterruptedException | TimeoutException e) {
                // If it was cancelled, just ignore it (don't log).
                return;
            } catch (Exception e) {
                LOG.error(e);
            }
        }

        @Override
        public Object getValue() {
            return psiFile;
        }

        @Override
        public @NotNull ItemPresentation getPresentation() {
            return new ItemPresentation() {
                @Override
                public @NlsSafe @Nullable String getPresentableText() {
                    return psiFile.getName();
                }

                @Override
                public @NlsSafe @Nullable String getLocationString() {
                    return psiFile.getVirtualFile().getCanonicalPath();
                }

                @Override
                public @Nullable Icon getIcon(boolean unused) {
                    return AllIcons.General.Settings;
                }
            };
        }

        @Override
        public TreeElement @NotNull [] getChildren() {
            return children;
        }

        @Override
        public void navigate(boolean requestFocus) {
            new OpenFileDescriptor(psiFile.getProject(), psiFile.getVirtualFile(), 0).navigate(requestFocus);
        }

        @Override
        public boolean canNavigate() {
            return true;
        }

        @Override
        public boolean canNavigateToSource() {
            return true;
        }
    }
}
