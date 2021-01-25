package robotframework.idea;

import com.intellij.extapi.psi.StubBasedPsiElementBase;
import com.intellij.psi.stubs.IStubElementType;
import com.intellij.psi.stubs.StubElement;
import org.jetbrains.annotations.NotNull;

public class RobotPsiElement extends StubBasedPsiElementBase {
    public RobotPsiElement(@NotNull StubElement stub, @NotNull IStubElementType nodeType) {
        super(stub, nodeType);
    }
}
