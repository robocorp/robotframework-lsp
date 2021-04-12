package robocorp.lsp.intellij;

import com.intellij.lang.ASTNode;
import com.intellij.lang.folding.CustomFoldingBuilder;
import com.intellij.lang.folding.FoldingDescriptor;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.TextRange;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.psi.impl.source.tree.LeafElement;
import org.eclipse.lsp4j.FoldingRange;
import org.eclipse.lsp4j.FoldingRangeRequestParams;
import org.eclipse.lsp4j.TextDocumentIdentifier;
import org.jetbrains.annotations.NotNull;
import robocorp.lsp.psi.LSPGenericPsiElement;
import robocorp.robot.intellij.RobotElementType;
import robocorp.robot.intellij.RobotPsiFile;

import java.util.List;
import java.util.concurrent.CancellationException;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.TimeUnit;

public class FeatureCodeFolding extends CustomFoldingBuilder {

    private static final Logger LOG = Logger.getInstance(FeatureCodeFolding.class);

    @Override
    protected void buildLanguageFoldRegions(@NotNull List<FoldingDescriptor> descriptors, @NotNull PsiElement root, @NotNull Document document, boolean quick) {
        if (quick) {
            return;
        }
        if (root instanceof RobotPsiFile) {
            RobotPsiFile robotPsiFile = (RobotPsiFile) root;
            LanguageServerDefinition languageDefinition = EditorUtils.getLanguageDefinition(robotPsiFile);
            if (languageDefinition == null) {
                return;
            }
            LanguageServerManager languageServerManager = LanguageServerManager.getInstance(languageDefinition);
            if (languageServerManager == null) {
                return;
            }
            Project project = robotPsiFile.getProject();
            String projectRoot = project.getBasePath();
            if (projectRoot == null) {
                return;
            }
            PsiFile containingFile = root.getContainingFile();
            if (containingFile == null) {
                return;
            }
            VirtualFile virtualFile = containingFile.getVirtualFile();
            if (virtualFile == null) {
                return;
            }
            String extension = virtualFile.getExtension();
            if (extension == null) {
                return;
            }

            try {
                LanguageServerCommunication comm = languageServerManager.getLanguageServerCommunication("." + extension, projectRoot, project);
                String uri = Uris.toUri(virtualFile);
                TextDocumentIdentifier textDocument = new TextDocumentIdentifier(uri);
                FoldingRangeRequestParams params = new FoldingRangeRequestParams(textDocument);
                CompletableFuture<List<FoldingRange>> foldingRanges = comm.getFoldingRanges(params);
                if (foldingRanges == null) {
                    return;
                }
                List<FoldingRange> foldingRangeList;
                try {
                    foldingRangeList = foldingRanges.get(Timeouts.getFoldingRangeTimeout(), TimeUnit.SECONDS);
                    if (foldingRangeList == null) {
                        return;
                    }
                } catch (ProcessCanceledException | CompletionException | CancellationException | InterruptedException ignored) {
                    // Cancelled (InterruptedException is thrown when completion.cancel(true) is called from another thread).
                    return;
                }

                for (FoldingRange foldingRange : foldingRangeList) {

                    int startOffset;
                    int endOffset;
                    String text;
                    try {
                        int startLine = foldingRange.getStartLine();
                        startOffset = document.getLineStartOffset(startLine);
                        text = document.getText(new TextRange(startOffset, document.getLineEndOffset(startLine)));
                        endOffset = document.getLineEndOffset(foldingRange.getEndLine());
                    } catch (Exception e) {
                        return;
                    }

                    @NotNull TextRange range = new TextRange(startOffset, endOffset);

                    LSPGenericPsiElement psiElement = new LSPGenericPsiElement(project, robotPsiFile, text, startOffset, endOffset);
                    LeafElement element = new LeafElement(RobotElementType.DEFAULT, text) {
                        @Override
                        public PsiElement getPsi() {
                            return psiElement;
                        }
                    };

                    @NotNull ASTNode node = element;
                    descriptors.add(new FoldingDescriptor(node, range));
                }
            } catch (Exception e) {
                LOG.error(e);
                return;
            }

        }
    }

    @Override
    protected String getLanguagePlaceholderText(@NotNull ASTNode node, @NotNull TextRange range) {
        return node.getText();
    }

    @Override
    protected boolean isRegionCollapsedByDefault(@NotNull ASTNode node) {
        return false;
    }
}
