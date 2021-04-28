package robocorp.dap;

import com.intellij.execution.ui.ConsoleView;
import com.intellij.execution.ui.ConsoleViewContentType;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.xdebugger.XDebugSession;
import com.intellij.xdebugger.frame.XExecutionStack;
import com.intellij.xdebugger.frame.XStackFrame;
import org.eclipse.lsp4j.debug.Thread;
import org.eclipse.lsp4j.debug.*;
import org.eclipse.lsp4j.debug.services.IDebugProtocolClient;
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer;
import robocorp.dap.stack.DAPThreadInfo;
import robocorp.dap.stack.DAPTimeouts;

import java.lang.ref.WeakReference;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.*;

/**
 * This is the class where events from the debug adapter are received and
 * processed.
 * <p>
 * Note that while a message is being handled others aren't received, so,
 * most methods of this class forward the actual implementation to an
 * executor which will run what's needed in a different thread.
 * <p>
 * It's a single thread executor to still keep consistency of the order
 * in which messages are being received.
 */
public class DAPDebugProtocolClient implements IDebugProtocolClient {
    private static final Logger LOG = Logger.getInstance(DAPDebugProtocolClient.class);
    private final WeakReference<RobotDebugProcess> weakRobotDebugProcess;
    private final Executor singleThreadExecutor;

    // On updates it's always set as a whole (i.e.: it's immutable).
    private volatile Map<Integer, DAPThreadInfo> threadInfoMap = Collections.EMPTY_MAP;

    public DAPDebugProtocolClient(RobotDebugProcess robotDebugProcess, Executor singleThreadExecutor) {
        this.weakRobotDebugProcess = new WeakReference<>(robotDebugProcess);

        // Note: should be a single thread executor because we want to keep things in the same
        // order that they were submitted (we can't use it at the thread where the
        // events are received because otherwise it'd block receiving other messages
        // and requests inside the handler wouldn't really complete).
        this.singleThreadExecutor = singleThreadExecutor;
    }

    @Override
    public void initialized() {

    }

    @Override
    public void thread(ThreadEventArguments args) {
        singleThreadExecutor.execute(() -> {
            syncThreads();
        });
    }

    private Map<Integer, DAPThreadInfo> syncThreads() {
        RobotDebugProcess robotDebugProcess = this.weakRobotDebugProcess.get();
        if (robotDebugProcess == null) {
            threadInfoMap = Collections.EMPTY_MAP;
            return Collections.EMPTY_MAP;
        }
        IDebugProtocolServer remoteProxy = robotDebugProcess.getRemoteProxy();
        CompletableFuture<ThreadsResponse> threadsFuture = remoteProxy.threads();
        try {
            ThreadsResponse threadsResponse = threadsFuture.get(DAPTimeouts.getThreadsTimeout(), TimeUnit.SECONDS);
            Thread[] threads = threadsResponse.getThreads();

            Map<Integer, DAPThreadInfo> newMap = new HashMap<>();
            for (Thread t : threads) {
                DAPThreadInfo threadInfo = threadInfoMap.get(t.getId());
                if (threadInfo == null) {
                    threadInfo = new DAPThreadInfo(t.getId());
                }
                threadInfo.dapThread = t;
                newMap.put(t.getId(), threadInfo);
            }
            Map<Integer, DAPThreadInfo> unmodifiableMap = Collections.unmodifiableMap(newMap);
            this.threadInfoMap = unmodifiableMap;
            return unmodifiableMap;
        } catch (ExecutionException | TimeoutException | InterruptedException e) {
            LOG.error(e);
        }

        return Collections.EMPTY_MAP;
    }

    @Override
    public void stopped(StoppedEventArguments args) {
        singleThreadExecutor.execute(() -> {

            RobotDebugProcess robotDebugProcess = this.weakRobotDebugProcess.get();
            if (robotDebugProcess == null) {
                return;
            }
            Integer threadId = args.getThreadId();

            DAPThreadInfo thread = threadInfoMap.get(threadId);
            if (thread == null) {
                // If not available, sync with backend.
                Map<Integer, DAPThreadInfo> threads = syncThreads();
                thread = threads.get(threadId);
                if (thread == null) {
                    LOG.info("Trying to stop thread that no longer exists: " + args);
                    return;
                }
            }

            IDebugProtocolServer remoteProxy = robotDebugProcess.getRemoteProxy();
            StackTraceArguments stackTraceArguments = new StackTraceArguments();
            stackTraceArguments.setThreadId(threadId);
            CompletableFuture<StackTraceResponse> stackTrace = remoteProxy.stackTrace(stackTraceArguments);
            StackTraceResponse stackTraceResponse;
            try {
                stackTraceResponse = stackTrace.get(DAPTimeouts.getStackTraceTimeout(), TimeUnit.SECONDS);
            } catch (ExecutionException | TimeoutException | InterruptedException e) {
                LOG.error(e);
                return;
            }

            thread.updateState(DAPThreadInfo.State.SUSPENDED, stackTraceResponse);
            thread.setStopReason(args.getReason());
            thread.setMessage(args.getDescription());
            robotDebugProcess.threadSuspended(thread);
        });
    }

    @Override
    public void continued(ContinuedEventArguments args) {

    }

    @Override
    public void output(OutputEventArguments args) {
        singleThreadExecutor.execute(() -> {
            RobotDebugProcess robotDebugProcess = this.weakRobotDebugProcess.get();
            if (robotDebugProcess == null) {
                return;
            }
            XDebugSession session = robotDebugProcess.getSession();
            if (session == null) {
                return;
            }
            ConsoleView consoleView = session.getConsoleView();
            if (consoleView == null) {
                return;
            }
            String category = args.getCategory();
            ConsoleViewContentType contentType = ConsoleViewContentType.SYSTEM_OUTPUT;
            if ("stderr".equals(category)) {
                contentType = ConsoleViewContentType.ERROR_OUTPUT;
            }
            consoleView.print(args.getOutput(), contentType);
        });
    }

    public Collection<DAPThreadInfo> getThreads() {
        return threadInfoMap.values(); // Note: immutable collection.
    }
}
