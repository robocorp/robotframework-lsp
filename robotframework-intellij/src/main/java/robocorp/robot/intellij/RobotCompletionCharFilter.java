package robocorp.robot.intellij;

import com.intellij.codeInsight.lookup.CharFilter;
import com.intellij.codeInsight.lookup.Lookup;
import com.intellij.codeInsight.lookup.LookupElement;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.FeatureCodeCompletion;

public class RobotCompletionCharFilter extends CharFilter {
    @Override
    public @Nullable Result acceptChar(char c, int prefixLength, Lookup lookup) {
        LookupElement currentItem = lookup.getCurrentItem();
        if (currentItem instanceof FeatureCodeCompletion.LanguageServerLookupElement) {
            return Result.ADD_TO_PREFIX;
        }
        return null;
    }
}
