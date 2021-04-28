package robocorp.dap;

import com.intellij.execution.ExecutionException;
import com.intellij.execution.ExecutionManager;
import com.intellij.execution.ExecutionResult;
import com.intellij.execution.Executor;
import com.intellij.execution.configurations.RunProfile;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.execution.runners.ProgramRunner;
import com.intellij.execution.ui.RunContentDescriptor;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.wm.ToolWindowId;
import com.intellij.xdebugger.XDebugProcess;
import com.intellij.xdebugger.XDebugProcessStarter;
import com.intellij.xdebugger.XDebugSession;
import com.intellij.xdebugger.XDebuggerManager;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.concurrency.AsyncPromise;

/**
 * This class is responsible for forwarding the run to the proper class
 * as well as the related debug session in the intellij side.
 * <p>
 * Note that the flow is the same in run or debug mode (the only difference
 * is that that the `noDebug` flag passed to the debug adapter is different).
 */
public class RobotProgramRunner implements ProgramRunner {
    @Override
    public @NotNull
    @NonNls
    String getRunnerId() {
        return "RobotFramework";
    }

    @Override
    public boolean canRun(@NotNull String executorId, @NotNull RunProfile profile) {
        if (profile instanceof RobotRunProfileOptionsEditionAndPersistence) {
            if (ToolWindowId.RUN.equals(executorId)) {
                return true;
            } else if (ToolWindowId.DEBUG.equals(executorId)) {
                return true;
            }
        }
        return false;
    }

    @Override
    public void execute(@NotNull ExecutionEnvironment env) throws ExecutionException {
        final RobotRunProfileStateRobotDAPStarter state = (RobotRunProfileStateRobotDAPStarter) env.getState();
        ExecutionManager executionManager = ExecutionManager.getInstance(env.getProject());

        FileDocumentManager.getInstance().saveAllDocuments();
        Executor executor = env.getExecutor();

        executionManager.startRunProfile(env, () -> {
            AsyncPromise<RunContentDescriptor> promise = new AsyncPromise<>();

            ExecutionResult executionResult;
            try {
                executionResult = state.execute(executor, this);
                // At this point the debug adapter is running (but still not executing any target code
                // as we still didn't do the launch/configurationDone).
                if (executionResult == null) {
                    promise.setResult(null);
                    return promise;
                }

                final XDebuggerManager debuggerManager = XDebuggerManager.getInstance(env.getProject());
                final XDebugSession debugSession = debuggerManager.startSession(env, new XDebugProcessStarter() {
                    @Override
                    @NotNull
                    public XDebugProcess start(@NotNull final XDebugSession session) throws ExecutionException {
                        try {
                            return new RobotDebugProcess(executor, session, executionResult.getProcessHandler());
                        } catch (Exception e) {
                            throw new ExecutionException(e);
                        }
                    }
                });
                promise.setResult(debugSession.getRunContentDescriptor());
                return promise;
            } catch (ExecutionException e) {
                promise.setError(e);
                return promise;
            }
        });
    }
}
