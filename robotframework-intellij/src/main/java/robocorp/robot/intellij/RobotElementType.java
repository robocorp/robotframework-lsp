package robocorp.robot.intellij;

import com.intellij.psi.tree.IElementType;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;

public class RobotElementType extends IElementType {
    public RobotElementType(@NotNull @NonNls String debugName) {
        super(debugName, RobotFrameworkLanguage.INSTANCE);
    }

    public static final RobotElementType NEW_LINE = new RobotElementType("NEW_LINE");
    public static final RobotElementType WHITESPACE = new RobotElementType("WHITESPACE");
    public static final RobotElementType HEADING = new RobotElementType("HEADING");
    public static final RobotElementType DEFAULT = new RobotElementType("DEFAULT");
    public static final RobotElementType COMMENT = new RobotElementType("COMMENT");
    public static final RobotElementType VARIABLE = new RobotElementType("VARIABLE");
}