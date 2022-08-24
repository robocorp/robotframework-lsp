package robocorp.robot.intellij;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.fileTypes.FileTypeManager;
import com.intellij.openapi.fileTypes.FileTypeRegistry;
import com.intellij.openapi.fileTypes.LanguageFileType;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.lsp.intellij.EditorUtils;

import javax.swing.*;

public class RobotFrameworkFileType extends LanguageFileType {

    public static final RobotFrameworkFileType INSTANCE = new RobotFrameworkFileType();

    private RobotFrameworkFileType() {
        super(RobotFrameworkLanguage.INSTANCE);
        ApplicationManager.getApplication().invokeLater(() -> {
            EditorUtils.runWriteAction(() -> {
                FileTypeManager instance = (FileTypeManager) FileTypeRegistry.getInstance();
                instance.associateExtension(RobotFrameworkFileType.INSTANCE, "resource");
                instance.associateExtension(RobotFrameworkFileType.INSTANCE, "robot");
            });
        });
    }

    @NotNull
    @Override
    public String getName() {
        return "Robot Framework";
    }

    @NotNull
    @Override
    public String getDescription() {
        return "Robot Framework";
    }

    @NotNull
    @Override
    public String getDefaultExtension() {
        return "robot";
    }

    @Nullable
    @Override
    public Icon getIcon() {
        return RobotFrameworkIcons.FILE;
    }

}