package robocorp.dap.stack;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.xdebugger.XSourcePosition;
import com.intellij.xdebugger.evaluation.XDebuggerEvaluator;
import org.eclipse.lsp4j.debug.EvaluateArguments;
import org.eclipse.lsp4j.debug.EvaluateResponse;
import org.eclipse.lsp4j.debug.Variable;
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import robocorp.dap.RobotDebugProcess;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

public class DAPDebuggerEvaluator extends XDebuggerEvaluator {

    private final DAPStackFrame dapStackFrame;

    public DAPDebuggerEvaluator(DAPStackFrame dapStackFrame) {
        this.dapStackFrame = dapStackFrame;
    }

    @Override
    public void evaluate(@NotNull String expression, @NotNull XEvaluationCallback callback, @Nullable XSourcePosition expressionPosition) {
        ApplicationManager.getApplication().executeOnPooledThread(() -> {
            RobotDebugProcess debugProcess = dapStackFrame.getDebugProcess();
            if (expression.isEmpty()) {
                Variable variable = new Variable();
                variable.setName("<Empty evaluation>");
                variable.setValue("<Empty evaluation>");
                callback.evaluated(new DAPDebugVariable(variable, debugProcess));
                return;
            }

            IDebugProtocolServer remoteProxy = debugProcess.getRemoteProxy();
            EvaluateArguments args = new EvaluateArguments();
            args.setFrameId(dapStackFrame.getFrameInfo().getId());
            args.setExpression(expression);
            CompletableFuture<EvaluateResponse> completableFuture = remoteProxy.evaluate(args);
            try {
                EvaluateResponse evaluateResponse = completableFuture.get(DAPTimeouts.getEvaluateTimeout(), TimeUnit.SECONDS);
                Variable variable = new Variable();
                variable.setName(expression);
                variable.setValue(evaluateResponse.getResult());
                callback.evaluated(new DAPDebugVariable(variable, debugProcess));
            } catch (Exception e) {
                callback.errorOccurred(e.getMessage());
            }

        });
    }
}
