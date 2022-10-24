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

export enum InspectorType {
    Browser = "browser",
    Windows = "windows",
    Image = "image",
    WebRecorder = "web-recorder",
}

export type InspectorTypes = `${InspectorType}`;

export const DEFAULT_INSPECTOR_VALUE = {
    browser: false,
    image: false,
    windows: false,
    "web-recorder": false,
};

let _openingInspector: { [K in InspectorTypes]: boolean } = DEFAULT_INSPECTOR_VALUE;
let _startingRootWindowNotified: { [K in InspectorTypes]: boolean } = DEFAULT_INSPECTOR_VALUE;

export async function openRobocorpInspector(locatorType?: InspectorTypes, locator?: LocatorEntry): Promise<void> {
    const localLocatorType = locatorType !== undefined ? locatorType : InspectorType.Browser;
    if (localLocatorType === InspectorType.Windows && process.platform !== "win32") {
        window.showInformationMessage("This feature is Windows specific and not supported on other platforms.");
        return; // Windows only feature
    }

    if (_openingInspector[localLocatorType]) {
        if (!_startingRootWindowNotified[localLocatorType]) {
            return; // We should be showing the progress already, so, don't do anything.
        }
        window.showInformationMessage(
            "The Locators UI is already opened, so, please use the existing UI (or close it/wait for it to be closed)."
        );
        return;
    }
    try {
        _openingInspector[localLocatorType] = true;
        return await _internalOpenRobocorpInspector(localLocatorType, locator);
    } finally {
        _openingInspector[localLocatorType] = false;
        _startingRootWindowNotified[localLocatorType] = false;
    }
}

export async function _internalOpenRobocorpInspector(
    locatorType?: InspectorTypes,
    locator?: LocatorEntry
): Promise<void> {
    let locatorJson;
    const args: string[] = [];
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
        // if locatorType is given prioritize that. Else Ensure that a locator is selected!
        args.push("open");
        args.push(locatorType);
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
                    _startingRootWindowNotified[locatorType] = true;
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
        await startInspectorCLI(
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
