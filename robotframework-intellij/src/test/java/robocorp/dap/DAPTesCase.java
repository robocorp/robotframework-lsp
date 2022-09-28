package robocorp.dap;

import com.intellij.execution.Executor;
import com.intellij.execution.RunnerAndConfigurationSettings;
import com.intellij.execution.executors.DefaultDebugExecutor;
import com.intellij.execution.impl.RunManagerImpl;
import com.intellij.execution.impl.RunnerAndConfigurationSettingsImpl;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.execution.runners.ProgramRunner;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiFile;
import org.eclipse.lsp4j.debug.*;
import org.eclipse.lsp4j.debug.launch.DSPLauncher;
import org.eclipse.lsp4j.debug.services.IDebugProtocolClient;
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer;
import org.eclipse.lsp4j.jsonrpc.Launcher;
import org.jetbrains.concurrency.AsyncPromise;
import org.junit.Assert;
import org.junit.Test;
import robocorp.lsp.intellij.LSPTesCase;

import java.io.File;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

public class DAPTesCase extends LSPTesCase {

    private static final Logger LOG = Logger.getInstance(DAPTesCase.class);

    public static class DAPTestClient implements IDebugProtocolClient {

        public volatile AsyncPromise<StoppedEventArguments> onStopped = new AsyncPromise<StoppedEventArguments>();
        public volatile AsyncPromise<TerminatedEventArguments> onTerminated = new AsyncPromise<TerminatedEventArguments>();
        public volatile AsyncPromise<ExitedEventArguments> onExited = new AsyncPromise<ExitedEventArguments>();

        @Override
        public void stopped(StoppedEventArguments args) {
            onStopped.setResult(args);
            onStopped = new AsyncPromise();
        }

        @Override
        public void terminated(TerminatedEventArguments args) {
            onTerminated.setResult(args);
            // Don't reset the promise as a single terminate is expected.
        }

        @Override
        public void exited(ExitedEventArguments args) {
            onExited.setResult(args);
            // Don't reset the promise as a single exit is expected.
        }
    }

    @Test
    public void testDAPBasic() throws Exception {
        // A basic test of debugging: create launch, set breakpoint, run, wait for breakpoint, continue.

        // Intellij requires LOTS of scaffolding...
        Executor executor = new DefaultDebugExecutor();
        ProgramRunner runner = new RobotProgramRunner();
        RobotConfigurationType robotConfigurationType = new RobotConfigurationType();
        RobotConfigurationFactory factory = new RobotConfigurationFactory(robotConfigurationType);
        RobotRunProfileOptionsEditionAndPersistence configuration = new RobotRunProfileOptionsEditionAndPersistence(getProject(), factory, "Test config name");
        RobotLaunchConfigRunOptions options = configuration.getOptions();
        PsiFile[] psiFiles = myFixture.configureByFiles("case1.robot", "case1_library.py");
        VirtualFile targetVirtualFile = psiFiles[0].getVirtualFile();
        options.target = targetVirtualFile.getPath();
        options.env = new HashMap<>();
        options.env.put("ROBOTFRAMEWORK_DAP_LOG_FILENAME", new File(myFixture.getTempDirPath(), "dap.log").getAbsolutePath());
        options.env.put("ROBOTFRAMEWORK_DAP_LOG_LEVEL", "3");
        options.env.put("PYTHONPATH", new File(targetVirtualFile.getPath()).getParent());

        RunManagerImpl impl = RunManagerImpl.getInstanceImpl(getProject());
        RunnerAndConfigurationSettings settings = new RunnerAndConfigurationSettingsImpl(impl, configuration);
        ExecutionEnvironment executionEnv = new ExecutionEnvironment(executor, runner, settings, getProject());
        RobotRunProfileStateRobotDAPStarter robotRunProfileStateRobotDAPStarter = (RobotRunProfileStateRobotDAPStarter) configuration.getState(executor, executionEnv);

        // At this point we actually created the process.
        RobotRunProfileStateRobotDAPStarter.RobotProcessHandler processHandler = (RobotRunProfileStateRobotDAPStarter.RobotProcessHandler) robotRunProfileStateRobotDAPStarter.startProcess();
        DAPTestClient client = new DAPTestClient();
        InputStream in = processHandler.getDebugAdapterProcess().getInputStream();
        OutputStream out = processHandler.getDebugAdapterProcess().getOutputStream();
        PrintWriter trace = new PrintWriter(System.out);

        // Actually connect using the DAP with in/out streams.
        Launcher<IDebugProtocolServer> launcher = DSPLauncher.createClientLauncher(client, in, out, false, trace);

        launcher.startListening();
        InitializeRequestArguments arguments = new InitializeRequestArguments();
        arguments.setClientID("intellij");
        arguments.setAdapterID("RobotFramework");
        arguments.setPathFormat("path");
        arguments.setLinesStartAt1(true);
        arguments.setColumnsStartAt1(true);
        arguments.setSupportsRunInTerminalRequest(false);

        IDebugProtocolServer remoteProxy = launcher.getRemoteProxy();
        Capabilities capabilities = remoteProxy.initialize(arguments).get(10, TimeUnit.SECONDS);
        Assert.assertTrue(capabilities.getSupportsConfigurationDoneRequest());

        Map<String, Object> launchArgs = new HashMap<>();
        launchArgs.put("terminal", "none");
        launchArgs.put("target", targetVirtualFile.getPath());
        launchArgs.put("noDebug", false);
        launchArgs.put("__sessionId", "sessionId");
        launchArgs.put("env", options.env);
        CompletableFuture<Void> launch = remoteProxy.launch(launchArgs);
        launch.get(10, TimeUnit.SECONDS);

        SetBreakpointsArguments breakpointArgs = new SetBreakpointsArguments();
        Source source = new Source();
        source.setName(targetVirtualFile.getName());
        source.setPath(targetVirtualFile.getPath());
        breakpointArgs.setSource(source);
        SourceBreakpoint sourceBreakpoint = new SourceBreakpoint();
        sourceBreakpoint.setLine(6);
        SourceBreakpoint[] breakpoints = new SourceBreakpoint[]{sourceBreakpoint};
        breakpointArgs.setBreakpoints(breakpoints);
        CompletableFuture<SetBreakpointsResponse> future = remoteProxy.setBreakpoints(breakpointArgs);
        SetBreakpointsResponse setBreakpointsResponse = future.get(10, TimeUnit.SECONDS);
        Breakpoint[] breakpoints1 = setBreakpointsResponse.getBreakpoints();
        Assert.assertEquals(1, breakpoints1.length);
        Assert.assertTrue(breakpoints1[0].isVerified());

        AsyncPromise<StoppedEventArguments> onStopped = client.onStopped;
        remoteProxy.configurationDone(new ConfigurationDoneArguments());
        StoppedEventArguments stoppedEventArguments = onStopped.get(10, TimeUnit.SECONDS);
        Assert.assertTrue(stoppedEventArguments.getAllThreadsStopped());

        CompletableFuture<ContinueResponse> continue_ = remoteProxy.continue_(new ContinueArguments());
        continue_.get(10, TimeUnit.SECONDS);

        client.onTerminated.get(10, TimeUnit.SECONDS);

        // Check that the dap process actually exited.
        Assert.assertTrue(processHandler.getProcess().waitFor(5, TimeUnit.SECONDS));
    }

}
