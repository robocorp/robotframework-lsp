import * as path from "path";
import { ProgressLocation, window } from "vscode";
import { getLanguageServerPythonInfo } from "./extension";
import { verifyFileExists } from "./files";
import { listAndAskRobotSelection } from "./activities";
import { getSelectedLocator, getSelectedRobot, LocatorEntry, RobotEntry } from "./viewsCommon";
import { execFilePromise, ExecFileReturn, mergeEnviron } from "./subprocess";
import { OUTPUT_CHANNEL } from "./channel";
import { ChildProcess } from "child_process";
import { feedback } from "./rcc";

let _openingInspector: boolean = false;
let _startingRootWindowNotified: boolean = false;

export async function openRobocorpInspector(locatorType?: string, locator?: LocatorEntry): Promise<void> {
    if (locatorType === "windows" && process.platform !== "win32") {
        window.showInformationMessage("This feature is Windows specific and not supported on other platforms.");
        return; // Windows only feature
    }

    if (_openingInspector) {
        if (!_startingRootWindowNotified) {
            return; // We should be showing the progress already, so, don't do anything.
        }
        window.showInformationMessage(
            "The Locators UI is already opened, so, please use the existing UI (or close it/wait for it to be closed)."
        );
        return;
    }
    try {
        _openingInspector = true;
        return await _internalOpenRobocorpInspector(locatorType, locator);
    } finally {
        _openingInspector = false;
        _startingRootWindowNotified = false;
    }
}

export async function _internalOpenRobocorpInspector(locatorType?: string, locator?: LocatorEntry): Promise<void> {
    let locatorJson;
    const args: string[] = [];
    let selectedEntry: RobotEntry = getSelectedRobot({
        noSelectionMessage: "Please select a robot first.",
    });
    let robot: LocalRobotMetadataInfo | undefined = selectedEntry?.robot;
    if (!robot) {
        // Ask for the robot to be used and then show dialog with the options.
        robot = await listAndAskRobotSelection(
            "Please select the Robot where the locators should be saved.",
            "Unable to create locator (no Robot detected in the Workspace)."
        );
        if (!robot) {
            return;
        }
    }
    locatorJson = path.join(robot.directory, "locators.json");
    locatorJson = verifyFileExists(locatorJson, false) ? locatorJson : undefined;
    const inspectorLaunchInfo = await getLanguageServerPythonInfo();
    if (!inspectorLaunchInfo) {
        OUTPUT_CHANNEL.appendLine("Unable to get Robocorp Inspector launch info.");
        return;
    }

    // add locators.json path to args
    if (locatorJson) {
        args.push("--database", locatorJson);
    }

    if (locatorType) {
        if (locatorType == "record") {
            // TODO: implement code to integrate recording output to locators.json
            OUTPUT_CHANNEL.appendLine("Recording.");
            args.push("add");
            args.push("recorder");
        }
        // if locatorType is given prioritize that. Else Ensure that a locator is selected!
        else {
            args.push("add");
            args.push(locatorType);
        }
    } else {
        const locatorSelected: LocatorEntry | undefined =
            locator ??
            (await getSelectedLocator({
                noSelectionMessage: "Please select a locator first.",
                moreThanOneSelectionMessage: "Please select only one locator.",
            }));
        if (locatorSelected.type === "error") {
            OUTPUT_CHANNEL.appendLine("Trying to edit non-existing locator.");
            return;
        }
        if (locatorSelected) {
            args.push("edit", locatorSelected.name);
        } else {
            OUTPUT_CHANNEL.appendLine("Unable to open Robocorp Inspector. Select a locator first.");
            return;
        }
    }

    let resolveProgress = undefined;
    window.withProgress(
        {
            location: ProgressLocation.Notification,
            title: "Robocorp",
            cancellable: false,
        },
        (progress) => {
            progress.report({ message: "Opening Inspector..." });
            return new Promise<void>((resolve) => {
                resolveProgress = resolve;
            });
        }
    );

    try {
        // Required due to how conda packages python, and MacOS requiring
        // a signed package for displaying windows (supplied through python.app)
        function replaceNewLines(s) {
            return s.replace(/(?:\r\n|\r|\n)/g, "\n  i> ");
        }
        let first = true;
        function append(s: string) {
            if (first) {
                OUTPUT_CHANNEL.append("  i> ");
                first = false;
            }
            OUTPUT_CHANNEL.append(replaceNewLines(s));
        }
        const configChildProcess = function (childProcess: ChildProcess) {
            childProcess.stderr.on("data", function (data: any) {
                const s = "" + data;
                append(s);
                if (s.includes("Starting root window")) {
                    _startingRootWindowNotified = true;
                    resolveProgress();
                }
            });
            childProcess.stdout.on("data", function (data: any) {
                append("" + data);
            });
        };

        feedback("vscode.inspector.opened", locatorType);

        const pythonExecutablePath =
            process.platform === "darwin"
                ? path.join(path.dirname(inspectorLaunchInfo.pythonExe), "pythonw")
                : inspectorLaunchInfo.pythonExe;
        const launchResult: ExecFileReturn = await startInspectorCLI(
            pythonExecutablePath,
            args,
            robot.directory,
            inspectorLaunchInfo.environ,
            configChildProcess
        );
    } finally {
        resolveProgress();
    }
}

async function startInspectorCLI(
    pythonExecutable: string,
    args: string[],
    cwd?: string,
    environ?: { [key: string]: string },
    configChildProcess?: (childProcess: ChildProcess) => void
): Promise<ExecFileReturn> {
    const inspectorCmd = ["-m", "inspector.cli"];
    const completeArgs = inspectorCmd.concat(args);
    OUTPUT_CHANNEL.appendLine(`Using cwd root for inspector: "${cwd}"`);
    return execFilePromise(
        pythonExecutable,
        completeArgs,
        {
            env: mergeEnviron(environ),
            cwd,
        },
        {
            "configChildProcess": configChildProcess,
        }
    );
}
