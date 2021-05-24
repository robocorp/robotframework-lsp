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
    public static final RobotElementType PARAMETER_NAME = new RobotElementType("PARAMETER_NAME");
    public static final RobotElementType ARGUMENT_VALUE = new RobotElementType("ARGUMENT_VALUE");
    public static final RobotElementType NAME = new RobotElementType("NAME");
    public static final RobotElementType SETTING = new RobotElementType("SETTING");
    public static final RobotElementType KEYWORD = new RobotElementType("KEYWORD");
    public static final RobotElementType VARIABLE_OPERATOR = new RobotElementType("VARIABLE_OPERATOR");
    public static final RobotElementType KEYWORD_CALL = new RobotElementType("KEYWORD_CALL");
    public static final RobotElementType SETTING_OPERATOR = new RobotElementType("SETTING_OPERATOR");
    public static final RobotElementType CONTROL = new RobotElementType("CONTROL");
    public static final RobotElementType TEST_CASE_NAME = new RobotElementType("TEST_CASE_NAME");
}