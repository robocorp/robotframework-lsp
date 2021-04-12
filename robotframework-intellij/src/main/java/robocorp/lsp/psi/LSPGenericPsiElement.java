package robocorp.lsp.psi;

import com.intellij.lang.ASTNode;
import com.intellij.lang.Language;
import com.intellij.openapi.fileEditor.OpenFileDescriptor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.NlsSafe;
import com.intellij.openapi.util.TextRange;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.*;
import com.intellij.psi.impl.PsiElementBase;
import org.eclipse.lsp4j.Position;
import org.eclipse.lsp4j.Range;
import org.eclipse.lsp4j.TextDocumentIdentifier;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.LanguageServerDefinition;

public class LSPGenericPsiElement extends PsiElementBase implements PsiNameIdentifierOwner, NavigatablePsiElement {

    public static class LSPGenericPsiReference extends PsiReferenceBase<PsiElement> {
        public LSPGenericPsiReference(LSPGenericPsiElement lspGenericPsiElement) {
            super(lspGenericPsiElement);
        }

        @Override
        public @Nullable PsiElement resolve() {
            return getElement();
        }

        @Override
        protected TextRange calculateDefaultRangeInElement() {
            return new TextRange(0, getElement().getTextLength());
        }
    }

    private final Project project;
    private final PsiFile file;

    // Would change on a rename...
    private String text;

    public final int startOffset;
    public final int endOffset;
    public final Range startRange;

    public final TextDocumentIdentifier originalId;
    public final Position originalPos;
    public final LanguageServerDefinition languageDefinition;

    public LSPGenericPsiElement(@NotNull Project project, @NotNull PsiFile file, @NotNull String text, int startOffset, int endOffset, Range startRange, TextDocumentIdentifier originalId, Position originalPos, LanguageServerDefinition languageDefinition) {
        this.project = project;
        this.file = file;
        this.text = text;
        this.startOffset = startOffset;
        this.endOffset = endOffset;
        this.startRange = startRange;
        this.originalId = originalId;
        this.originalPos = originalPos;
        this.languageDefinition = languageDefinition;
    }

    public LSPGenericPsiElement(@NotNull Project project, @NotNull PsiFile file, @NotNull String text, int startOffset, int endOffset) {
        this.project = project;
        this.file = file;
        this.text = text;
        this.startOffset = startOffset;
        this.endOffset = endOffset;
        this.startRange = null;
        this.originalId = null;
        this.originalPos = null;
        this.languageDefinition = null;
    }

    @Override
    public ASTNode getNode() {
        return null;
    }

    @Override
    public PsiReference getReference() {
        return new LSPGenericPsiReference(this);
    }

    @Override
    @NotNull
    public Language getLanguage() {
        return file.getLanguage();
    }

    @Override
    public PsiElement @NotNull [] getChildren() {
        return new PsiElement[0];
    }

    @Override
    public PsiElement getParent() {
        return this.file;
    }

    @Override
    public String toString() {
        if (text.length() > 0) {
            return text + " at: " + file.getName() + " line: " + startRange.getStart().getLine() + 1;
        }
        return file.getName() + " line: " + startRange.getStart().getLine() + 1;
    }

    @Override
    public PsiElement setName(@NotNull String name) {
        this.text = name;
        return this;
    }

    @Override
    public void navigate(boolean requestFocus) {
        VirtualFile file = getContainingFile().getVirtualFile();
        if (file != null) {
            OpenFileDescriptor descriptor = new OpenFileDescriptor(getProject(), file, startOffset);
            descriptor.navigate(requestFocus);
        }
    }

    @Override
    public PsiFile getContainingFile() {
        return file;
    }

    @Override
    public TextRange getTextRange() {
        return new TextRange(startOffset, endOffset);
    }

    @Override
    public int getStartOffsetInParent() {
        return startOffset;
    }

    @Override
    public int getTextLength() {
        return endOffset - startOffset;
    }

    @Override
    public @Nullable PsiElement findElementAt(int offset) {
        return null;
    }

    @Override
    @NotNull
    public Project getProject() {
        return project;
    }

    @Override
    public int getTextOffset() {
        return startOffset;
    }

    @Override
    public @NlsSafe String getText() {
        return text;
    }

    @Override
    public char @NotNull [] textToCharArray() {
        return text.toCharArray();
    }

    @Override
    public @Nullable PsiElement getNameIdentifier() {
        return this;
    }
}
