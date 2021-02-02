package robocorp.lsp.psi;

import com.intellij.extapi.psi.ASTWrapperPsiElement;
import com.intellij.lang.ASTNode;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.util.TextRange;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiReference;
import com.intellij.psi.PsiReferenceBase;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.FeatureDefinition;

/**
 * The parser (instance of com.intellij.lang.ParserDefinition) must generate these
 * elements so that the go to definition works!
 */
public class LSPPsiAstElement extends ASTWrapperPsiElement {

    public static class LSPReference extends PsiReferenceBase<PsiElement> {

        private static final Logger LOG = Logger.getInstance(LSPReference.class);

        public LSPReference(LSPPsiAstElement psiElement) {
            super(psiElement);
        }

        @Override
        protected TextRange calculateDefaultRangeInElement() {
            return new TextRange(0, getElement().getTextLength());
        }

        @Override
        public @Nullable PsiElement resolve() {
            return FeatureDefinition.resolve(this);
        }

    }

    public LSPPsiAstElement(@NotNull ASTNode node) {
        super(node);
    }

    @Override
    public PsiReference getReference() {
        return new LSPReference(this);
    }

    @Override
    public PsiReference findReferenceAt(int offset) {
        // offset here is offset in element -- we know that we're a leaf so, just return the usual getReference().
        return getReference();
    }
}
