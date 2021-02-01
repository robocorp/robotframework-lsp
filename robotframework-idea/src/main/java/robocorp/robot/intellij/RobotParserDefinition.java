package robocorp.robot.intellij;

import com.intellij.lang.*;
import com.intellij.lexer.Lexer;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.project.Project;
import com.intellij.psi.FileViewProvider;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.psi.tree.IElementType;
import com.intellij.psi.tree.IFileElementType;
import com.intellij.psi.tree.ILightStubFileElementType;
import com.intellij.psi.tree.TokenSet;
import com.intellij.psi.util.PsiUtilCore;
import com.intellij.util.diff.FlyweightCapableTreeStructure;
import org.jetbrains.annotations.NotNull;
import robocorp.lsp.psi.LSPPsiAstElement;

class RobotParser implements PsiParser {

    private void doParse(@NotNull IElementType root, @NotNull PsiBuilder builder) {
        PsiBuilder.@NotNull Marker rootMarker = builder.mark();
        while (!builder.eof()) {
            IElementType tokenType = builder.getTokenType();
            PsiBuilder.@NotNull Marker mark = null;
            if (tokenType != null) {
                mark = builder.mark();
            }
            builder.advanceLexer();
            if (tokenType != null) {
                mark.done(tokenType);
            }
        }
        rootMarker.done(root);
    }

    @NotNull
    public FlyweightCapableTreeStructure<LighterASTNode> parseLight(IElementType root, PsiBuilder builder) {
        doParse(root, builder);
        return builder.getLightTree();
    }

    @Override
    public @NotNull ASTNode parse(@NotNull IElementType root, @NotNull PsiBuilder builder) {
        doParse(root, builder);
        return builder.getTreeBuilt();
    }

}

public class RobotParserDefinition implements ParserDefinition {

    private static final Logger LOG = Logger.getInstance(RobotParserDefinition.class);

    ILightStubFileElementType FILE = new ILightStubFileElementType(RobotFrameworkLanguage.INSTANCE) {
        @Override
        public FlyweightCapableTreeStructure<LighterASTNode> parseContentsLight(ASTNode chameleon) {
            PsiElement psi = chameleon.getPsi();
            assert psi != null : "Bad chameleon: " + chameleon;

            Project project = psi.getProject();
            PsiBuilderFactory factory = PsiBuilderFactory.getInstance();
            PsiBuilder builder = factory.createBuilder(project, chameleon);
            ParserDefinition parserDefinition = LanguageParserDefinitions.INSTANCE.forLanguage(getLanguage());
            assert parserDefinition != null : this;
            RobotParser parser = new RobotParser();
            return parser.parseLight(this, builder);
        }
    };

    @Override
    public @NotNull Lexer createLexer(Project project) {
        return new RobotLexer();
    }

    @Override
    public PsiParser createParser(Project project) {
        return new RobotParser();
    }

    @Override
    public IFileElementType getFileNodeType() {
        return FILE;
    }

    @Override
    public @NotNull TokenSet getCommentTokens() {
        return TokenSet.create(RobotElementType.COMMENT);
    }

    @Override
    public @NotNull TokenSet getStringLiteralElements() {
        return TokenSet.EMPTY;
    }

    @Override
    public @NotNull PsiElement createElement(ASTNode node) {
        final IElementType type = node.getElementType();
        if (type != null) {
            LSPPsiAstElement element = new LSPPsiAstElement(node);
            return element;
        }
        return PsiUtilCore.NULL_PSI_ELEMENT;
    }

    @Override
    public PsiFile createFile(FileViewProvider viewProvider) {
        return new RobotPsiFile(viewProvider, RobotFrameworkLanguage.INSTANCE);
    }
}
