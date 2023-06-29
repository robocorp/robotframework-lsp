import * as path from "path";
import { execFilePromise, mergeEnviron } from "./subprocess";
import { getLanguageServerPythonInfo } from "./extension";
import { InterpreterInfo, LocalRobotMetadataInfo } from "./protocols";
import { RobotEntry, getSelectedRobot } from "./viewsCommon";
import { listAndAskRobotSelection } from "./activities";
import { ChildProcess } from "child_process";
import { OUTPUT_CHANNEL } from "./channel";
import { ProgressLocation, window } from "vscode";

const replaceNewLines = (s) => {
    return s.replace(/(?:\r\n|\r|\n)/g, "\n  i> ");
};

const append = (s: string) => {
    OUTPUT_CHANNEL.append(replaceNewLines(s));
};

const runPythonWithMessage = async (
    cmd: string[],
    message: string,
    robot: LocalRobotMetadataInfo,
    successMsg?: string
) => {
    const pyLS = await getLanguageServerPythonInfo();
    const pythonExecutablePath =
        process.platform === "darwin" ? path.join(path.dirname(pyLS.pythonExe), "pythonw") : pyLS.pythonExe;

    let resolveProgress = undefined;
    window.withProgress(
        {
            location: ProgressLocation.Notification,
            title: "Robocorp",
            cancellable: false,
        },
        (progress) => {
            progress.report({ message: message });
            return new Promise<void>((resolve) => {
                resolveProgress = resolve;
            });
        }
    );

    const configChildProcess = (childProcess: ChildProcess) => {
        childProcess.stderr.on("data", (data: any) => {
            const s = "" + data;
            append(s);
            resolveProgress();
        });
        childProcess.stdout.on("data", (data: any) => {
            append("" + data);
        });
        childProcess.on("close", () => resolveProgress());
        childProcess.on("exit", () => resolveProgress());
        childProcess.on("disconnect", () => resolveProgress());
        childProcess.on("error", () => resolveProgress());
    };

    try {
        await execFilePromise(
            pythonExecutablePath,
            cmd,
            {
                env: mergeEnviron(pyLS.environ),
                cwd: robot.directory,
            },
            {
                "configChildProcess": configChildProcess,
            }
        );
    } catch (err) {
        // As the process is force-killed, we may have an error code in the return.
        // That's ok, just ignore it.
    }
};

export async function openPlaywrightRecorder(): Promise<void> {
    let selectedEntry: RobotEntry = getSelectedRobot();
    let robot: LocalRobotMetadataInfo | undefined = selectedEntry?.robot;
    if (robot === undefined) {
        // Ask for the robot to be used and then show dialog with the options.
        robot = await listAndAskRobotSelection(
            "Please select the Robot where the locators should be saved.",
            "Unable to open Inspector (no Robot detected in the Workspace)."
        );
        if (!robot) {
            return;
        }
    }

    await runPythonWithMessage(["-m", "playwright", "install"], "Installing Playwright drivers...", robot);
    await runPythonWithMessage(
        ["-m", "playwright", "codegen", "demo.playwright.dev/todomvc"],
        "Running Playwright Recorder...",
        robot
    );
}
