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
import com.intellij.util.diff.FlyweightCapableTreeStructure;
import org.jetbrains.annotations.NotNull;

class RobotParser implements PsiParser {

    private void doParse(@NotNull IElementType root, @NotNull PsiBuilder builder) {
        PsiBuilder.@NotNull Marker rootMarker = builder.mark();
        while (!builder.eof()) {
            builder.advanceLexer();
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
        return TokenSet.EMPTY;
    }

    @Override
    public @NotNull TokenSet getStringLiteralElements() {
        return TokenSet.EMPTY;
    }

    @Override
    public @NotNull PsiElement createElement(ASTNode node) {
        final IElementType type = node.getElementType();
        LOG.info("RobotParserDefinition: createElement being used (returned null).");
        // See: https://upsource.jetbrains.com/idea-ce/structure/idea-ce-4b94ba01122752d7576eb9d69638b6e89d1671b7/plugins/properties/properties-psi-impl/src/com/intellij/lang/properties/psi/impl
        // return new RobotPsiElement();
        return null;
    }

    @Override
    public PsiFile createFile(FileViewProvider viewProvider) {
        return new RobotPsiFile(viewProvider, RobotFrameworkLanguage.INSTANCE);
    }
}
