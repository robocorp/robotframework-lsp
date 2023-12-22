import * as path from "path";
import { env, ProgressLocation, Uri, window } from "vscode";
import { getLanguageServerPythonInfo } from "./extension";
import { verifyFileExists } from "./files";
import { listAndAskRobotSelection } from "./activities";
import { getSelectedLocator, getSelectedRobot, LocatorEntry, RobotEntry } from "./viewsCommon";
import { execFilePromise, mergeEnviron } from "./subprocess";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { ChildProcess } from "child_process";
import { feedback } from "./rcc";
import { LocalRobotMetadataInfo } from "./protocols";
import { Mutex } from "./mutex";

export enum InspectorType {
    Browser = "browser",
    Windows = "windows",
    Image = "image",
    Java = "java",
    WebRecorder = "web-recorder",
    PlaywrightRecorder = "playwright-recorder",
}

export type InspectorTypes = `${InspectorType}`;

export const DEFAULT_INSPECTOR_VALUE = {
    browser: false,
    image: false,
    windows: false,
    java: false,
    "web-recorder": false,
    "playwright-recorder": false,
};

let _openingInspector: { [K in InspectorTypes]: boolean } = DEFAULT_INSPECTOR_VALUE;
let _startingRootWindowNotified: { [K in InspectorTypes]: boolean } = DEFAULT_INSPECTOR_VALUE;

let globalVerifiedRequirementsForInspectorCli: boolean = false;
const globalVerifiedRequirementsForInspectorCliMutex = new Mutex();

export async function verifyWebview2Installed(
    pythonExecutable: string,
    cwd?: string,
    environ?: { [key: string]: string }
): Promise<boolean> {
    if (process.platform !== "win32") {
        return true; // If non-win32 that's Ok.
    }
    if (globalVerifiedRequirementsForInspectorCli) {
        return globalVerifiedRequirementsForInspectorCli;
    }
    return await globalVerifiedRequirementsForInspectorCliMutex.dispatch(async () => {
        while (!globalVerifiedRequirementsForInspectorCli) {
            try {
                const args = [
                    "-c",
                    "from webview.platforms.winforms import _is_chromium;print(_is_chromium());import sys;sys.stdout.flush()",
                ];
                const result = await execFilePromise(pythonExecutable, args, {
                    env: environ,
                    cwd,
                });

                const stdoutTrimmed = result.stdout.trim();
                if (stdoutTrimmed === "True") {
                    // Great, it's already there.
                    globalVerifiedRequirementsForInspectorCli = true;
                    return globalVerifiedRequirementsForInspectorCli;
                } else if (stdoutTrimmed === "False") {
                    // The user needs to install it.
                    const INSTALL_WEBVIEW2_OPTION = "Open Download Page";
                    let choice = await window.showWarningMessage(
                        `WebView2 Runtime not detected. To use locators the WebView2 Runtime is required.`,
                        {
                            "modal": true,
                            "detail": `Please download the installer from "https://developer.microsoft.com/en-us/microsoft-edge/webview2/".

Note: the "Evergreen Bootstrapper" is recommended, but the "Evergreen Standalone Installer" is also Ok.`,
                        },
                        INSTALL_WEBVIEW2_OPTION
                    );
                    if (choice == INSTALL_WEBVIEW2_OPTION) {
                        env.openExternal(
                            Uri.parse("https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section")
                        );
                        await window.showInformationMessage("Press Ok after installing WebView2 to proceed.", {
                            "modal": true,
                        });

                        // Keep on in the while loop to recheck.
                    } else {
                        // Cancelled.
                        return globalVerifiedRequirementsForInspectorCli;
                    }
                } else {
                    // This is unexpected.
                    throw new Error(
                        "Expected either 'True' or 'False' checking whether 'Webview2' is installed. Found: stdout:\n" +
                            result.stdout +
                            "\nstderr:\n" +
                            result.stderr
                    );
                }
            } catch (err) {
                logError("Error verifying if webview2 is available.", err, "ERROR_CHECK_WEBVIEW2");
                await window.showErrorMessage(
                    "There was an error verifying if webview2 is installed. Please submit an issue report to Robocorp."
                );
                return globalVerifiedRequirementsForInspectorCli;
            }
        }
        return globalVerifiedRequirementsForInspectorCli;
    });
}

export async function openRobocorpInspector(locatorType?: InspectorTypes, locator?: LocatorEntry): Promise<void> {
    let localLocatorType = locatorType;
    if (locatorType === undefined) {
        if (locator !== undefined) {
            localLocatorType = locator.type as InspectorTypes;
        } else {
            window.showErrorMessage("Internal error: either the locatorType or the locator entry must be specified.");
            return;
        }
    }
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

    if (locator !== undefined) {
        if (locator.type === "error") {
            OUTPUT_CHANNEL.appendLine("Trying to edit non-existing (error) locator.");
            return;
        }
        args.push("edit", locator.name);
    } else if (locatorType) {
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
            OUTPUT_CHANNEL.appendLine("Trying to edit non-existing (error) locator.");
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
): Promise<void> {
    const installed = await verifyWebview2Installed(pythonExecutable, cwd, environ);
    if (!installed) {
        return;
    }
    const inspectorCmd = ["-m", "inspector.cli"];
    const completeArgs = inspectorCmd.concat(args);
    OUTPUT_CHANNEL.appendLine(`Using cwd root for inspector: "${cwd}"`);
    try {
        await execFilePromise(
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
    } catch (err) {
        // As the process is force-killed, we may have an error code in the return.
        // That's ok, just ignore it.
    }
}
