package robocorp.robot.intellij;

import com.intellij.openapi.editor.colors.TextAttributesKey;
import com.intellij.openapi.fileTypes.SyntaxHighlighter;
import com.intellij.openapi.options.colors.AttributesDescriptor;
import com.intellij.openapi.options.colors.ColorDescriptor;
import com.intellij.openapi.options.colors.ColorSettingsPage;
import com.intellij.openapi.util.NlsContexts;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.util.Map;

public class RobotColorsPage implements ColorSettingsPage {

    private static final AttributesDescriptor[] ATTRIBUTES;

    static {
        ATTRIBUTES = new AttributesDescriptor[]{
                new AttributesDescriptor("color.settings.heading", RobotFrameworkSyntaxHighlightingFactory.HEADING),
                new AttributesDescriptor("color.settings.comment", RobotFrameworkSyntaxHighlightingFactory.COMMENT)
        };
    }

    @Override
    public @Nullable Icon getIcon() {
        return RobotFrameworkFileType.INSTANCE.getIcon();
    }

    @Override
    public @NotNull SyntaxHighlighter getHighlighter() {
        return new RobotFrameworkSyntaxHighlightingFactory().getSyntaxHighlighter(null, null);
    }

    @Override
    public @NonNls
    @NotNull String getDemoText() {
        return "*** Settings ***\nLibrary    Test\n# Comment\n";
    }

    @Override
    public @Nullable Map<String, TextAttributesKey> getAdditionalHighlightingTagToDescriptorMap() {
        return null;
    }

    @Override
    public AttributesDescriptor @NotNull [] getAttributeDescriptors() {
        return ATTRIBUTES;
    }

    @Override
    public ColorDescriptor @NotNull [] getColorDescriptors() {
        return new ColorDescriptor[0];
    }

    @Override
    public @NotNull @NlsContexts.ConfigurableName String getDisplayName() {
        return "Robot Framework";
    }
}
