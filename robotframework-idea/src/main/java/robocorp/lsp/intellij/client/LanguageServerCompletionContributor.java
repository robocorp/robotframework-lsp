package robocorp.lsp.intellij.client;

import com.intellij.codeInsight.completion.CompletionContributor;
import com.intellij.codeInsight.completion.CompletionParameters;
import com.intellij.codeInsight.completion.CompletionResultSet;
import com.intellij.openapi.diagnostic.Logger;
import org.jetbrains.annotations.NotNull;

public class LanguageServerCompletionContributor extends CompletionContributor {
    private static final Logger LOG = Logger.getInstance(LanguageServerCompletionContributor.class);

    public LanguageServerCompletionContributor(){
        System.out.println("Create");
    }

    @Override
    public void fillCompletionVariants(@NotNull CompletionParameters parameters, @NotNull CompletionResultSet result) {
        System.out.println("Completions here");
    }

}
