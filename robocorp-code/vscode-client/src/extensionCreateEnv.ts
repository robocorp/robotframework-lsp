"use strict";

import * as fs from "fs";
import * as path from "path";

import { workspace, window, Progress, ProgressLocation, ConfigurationTarget, env, Uri } from "vscode";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { getExtensionRelativeFile, verifyFileExists } from "./files";
import {
    collectBaseEnv,
    feedbackRobocorpCodeError,
    getRccLocation,
    getRobocorpHome,
    RCCDiagnostics,
    runConfigDiagnostics,
    STATUS_FATAL,
    STATUS_WARNING,
} from "./rcc";
import { Timing } from "./time";
import { execFilePromise, ExecFileReturn } from "./subprocess";
import { sleep } from "./time";
import { getProceedwithlongpathsdisabled, setProceedwithlongpathsdisabled } from "./robocorpSettings";
import { InterpreterInfo } from "./protocols";

export async function runAsAdmin(rccLocation: string, args: string[], env) {
    try {
        // Now, at this point we resolve the links to have a canonical location, because
        // we'll execute with a different user (i.e.: admin), we first resolve substs
        // which may not be available for that user (i.e.: a subst can be applied to one
        // account and not to the other) because path.resolve and fs.realPathSync don't
        // seem to resolve substed drives, we do it manually here.

        if (rccLocation.charAt(1) == ":") {
            // Check that we actually have a drive there.
            try {
                let resolved: string = fs.readlinkSync(rccLocation.charAt(0) + ":");
                rccLocation = path.join(resolved, rccLocation.slice(2));
            } catch (error) {
                // ignore (it's not a link)
            }
        }

        rccLocation = path.resolve(rccLocation);
        rccLocation = fs.realpathSync(rccLocation);
    } catch (error) {
        OUTPUT_CHANNEL.appendLine("Error (handled) resolving rcc canonical location: " + error);
    }
    rccLocation = rccLocation.split("\\").join("/"); // escape for the shell execute
    let argsAsStr = args.join(" ");
    let result: ExecFileReturn = await execFilePromise(
        "C:/Windows/System32/mshta.exe", // i.e.: Windows scripting
        [
            "javascript: var shell = new ActiveXObject('shell.application');" + // create a shell
                "shell.ShellExecute('" +
                rccLocation +
                "', '" +
                argsAsStr +
                "', '', 'runas', 1);close();", // runas will run in elevated mode
        ],
        { env: env }
    );
}

async function enableWindowsLongPathSupport(rccLocation: string) {
    try {
        try {
            // Expected failure if not admin.
            await execFilePromise(rccLocation, ["configure", "longpaths", "--enable"], { env: { ...process.env } });
            await sleep(100);
        } catch (error) {
            // Expected error (it means we need an elevated shell to run the command).
            await runAsAdmin(rccLocation, ["configure", "longpaths", "--enable"], { ...process.env });
            // Wait a second for the command to be executed as admin before proceeding.
            await sleep(1000);
        }
    } catch (error) {
        // Ignore here...
    }
}

async function isLongPathSupportEnabledOnWindows(rccLocation: string): Promise<boolean> {
    let enabled: boolean = true;
    let stdout = "<not collected>";
    let stderr = "<not collected>";
    try {
        let configureLongpathsOutput: ExecFileReturn = await execFilePromise(rccLocation, ["configure", "longpaths"], {
            env: { ...process.env },
        });
        stdout = configureLongpathsOutput.stdout;
        stderr = configureLongpathsOutput.stderr;
        if (stdout.indexOf("OK.") != -1 || stderr.indexOf("OK.") != -1) {
            enabled = true;
        } else {
            enabled = false;
        }
    } catch (error) {
        enabled = false;
        logError("There was some error with rcc configure longpaths.", error, "RCC_CONFIGURE_LONGPATHS");
    }
    if (enabled) {
        OUTPUT_CHANNEL.appendLine("Windows long paths support enabled");
    } else {
        OUTPUT_CHANNEL.appendLine(
            `Windows long paths support NOT enabled.\nRCC stdout:\n${stdout}\nRCC stderr:\n${stderr}`
        );
    }
    return enabled;
}

async function verifyLongPathSupportOnWindows(rccLocation: string): Promise<boolean> {
    if (process.env.ROBOCORP_OVERRIDE_SYSTEM_REQUIREMENTS) {
        // i.e.: When set we do not try to check (this flag makes "rcc configure longpaths"
        // return an error).
        return true;
    }
    if (process.platform == "win32") {
        while (true) {
            const proceed: boolean = getProceedwithlongpathsdisabled();
            if (proceed) {
                return true;
            }

            let enabled: boolean = await isLongPathSupportEnabledOnWindows(rccLocation);

            if (!enabled) {
                const YES = "Yes (requires admin)";
                const MANUALLY = "Open manual instructions";
                const NO = "No (don't warn again)";

                let result = await window.showErrorMessage(
                    "Windows long paths support is not enabled. Would you like to have Robocorp Code enable it now?",
                    {
                        "modal": true,
                        "detail":
                            "Note: it's possible to  proceed without enabling long paths, but keep in mind that may " +
                            "result in failures creating environments or running Robots if a dependency has long paths.",
                    },
                    YES,
                    MANUALLY,
                    NO
                    // Auto-cancel in modal
                );
                if (result == YES) {
                    // Enable it.
                    await enableWindowsLongPathSupport(rccLocation);
                    let enabled = await isLongPathSupportEnabledOnWindows(rccLocation);
                    if (enabled) {
                        return true;
                    } else {
                        let result = await window.showErrorMessage(
                            "It was not possible to automatically enable windows long path support. " +
                                "Please follow the instructions from https://robocorp.com/docs/troubleshooting/windows-long-path (press Ok to open in browser).",
                            { "modal": true },
                            "Ok"
                            // Auto-cancel in modal
                        );
                        if (result == "Ok") {
                            await env.openExternal(
                                Uri.parse("https://robocorp.com/docs/troubleshooting/windows-long-path")
                            );
                        }
                    }
                } else if (result == MANUALLY) {
                    await env.openExternal(Uri.parse("https://robocorp.com/docs/troubleshooting/windows-long-path"));
                } else if (result == NO) {
                    await setProceedwithlongpathsdisabled(true);
                    return true;
                } else {
                    // Cancel
                    OUTPUT_CHANNEL.appendLine(
                        "Extension will not be activated because Windows long paths support not enabled."
                    );
                    return false;
                }

                let resultOkLongPath = await window.showInformationMessage(
                    "Press Ok after Long Path support is manually enabled.",
                    { "modal": true },
                    "Ok"
                    // Auto-cancel in modal
                );
                if (!resultOkLongPath) {
                    OUTPUT_CHANNEL.appendLine(
                        "Extension will not be activated because Windows long paths support not enabled."
                    );
                    return false;
                }
            } else {
                return true;
            }
        }
    }
    return true;
}

/**
 * @returns the result of running `get_env_info.py`.
 */
export async function createDefaultEnv(
    progress: Progress<{ message?: string; increment?: number }>
): Promise<ExecFileReturn> | undefined {
    let robotConda: string;
    switch (process.platform) {
        case "darwin":
            robotConda = getExtensionRelativeFile("../../bin/create_env/conda_vscode_darwin_amd64.yaml");
            break;
        case "linux":
            robotConda = getExtensionRelativeFile("../../bin/create_env/conda_vscode_linux_amd64.yaml");
            break;
        case "win32":
            robotConda = getExtensionRelativeFile("../../bin/create_env/conda_vscode_windows_amd64.yaml");
            break;
        default:
            robotConda = getExtensionRelativeFile("../../bin/create_env/conda.yaml");
            break;
    }

    if (!robotConda) {
        OUTPUT_CHANNEL.appendLine("Unable to find: ../../bin/create_env/conda.yaml in extension.");
        feedbackRobocorpCodeError("INIT_CONDA_YAML_NOT_AVAILABLE");
        return;
    }

    const getEnvInfoPy = getExtensionRelativeFile("../../bin/create_env/get_env_info.py");
    if (!getEnvInfoPy) {
        OUTPUT_CHANNEL.appendLine("Unable to find: ../../bin/create_env/get_env_info.py in extension.");
        feedbackRobocorpCodeError("INIT_GET_ENV_INFO_FAIL");
        return;
    }

    let rccLocation = await getRccLocation();
    if (!rccLocation) {
        OUTPUT_CHANNEL.appendLine("Unable to get rcc executable location.");
        feedbackRobocorpCodeError("INIT_RCC_NOT_AVAILABLE");
        return;
    }

    // Check that the user has long names enabled on windows.
    if (!(await verifyLongPathSupportOnWindows(rccLocation))) {
        feedbackRobocorpCodeError("INIT_NO_LONGPATH_SUPPORT");
        return undefined;
    }
    // Check that ROBOCORP_HOME is valid (i.e.: doesn't have any spaces in it).
    let robocorpHome: string = await getRobocorpHome();

    let rccDiagnostics: RCCDiagnostics | undefined = await runConfigDiagnostics(rccLocation, robocorpHome);
    if (!rccDiagnostics) {
        let msg = "There was an error getting RCC diagnostics. Robocorp Code will not be started!";
        OUTPUT_CHANNEL.appendLine(msg);
        window.showErrorMessage(msg);
        feedbackRobocorpCodeError("INIT_NO_RCC_DIAGNOSTICS");
        return undefined;
    }

    while (!rccDiagnostics.isRobocorpHomeOk()) {
        const SELECT_ROBOCORP_HOME = "Set new ROBOCORP_HOME";
        const CANCEL = "Cancel";
        let result = await window.showInformationMessage(
            "The current ROBOCORP_HOME is invalid (paths with spaces/non ascii chars are not supported).",
            SELECT_ROBOCORP_HOME,
            CANCEL
        );
        if (!result || result == CANCEL) {
            OUTPUT_CHANNEL.appendLine("Cancelled setting new ROBOCORP_HOME.");
            feedbackRobocorpCodeError("INIT_INVALID_ROBOCORP_HOME");
            return undefined;
        }

        let uriResult = await window.showOpenDialog({
            "canSelectFolders": true,
            "canSelectFiles": false,
            "canSelectMany": false,
            "openLabel": "Set as ROBOCORP_HOME",
        });
        if (!uriResult) {
            OUTPUT_CHANNEL.appendLine("Cancelled getting ROBOCORP_HOME path.");
            feedbackRobocorpCodeError("INIT_CANCELLED_ROBOCORP_HOME");
            return undefined;
        }
        if (uriResult.length != 1) {
            OUTPUT_CHANNEL.appendLine("Expected 1 path to set as ROBOCORP_HOME. Found: " + uriResult.length);
            feedbackRobocorpCodeError("INIT_ROBOCORP_HOME_NO_PATH");
            return undefined;
        }
        robocorpHome = uriResult[0].fsPath;
        rccDiagnostics = await runConfigDiagnostics(rccLocation, robocorpHome);
        if (!rccDiagnostics) {
            let msg = "There was an error getting RCC diagnostics. Robocorp Code will not be started!";
            OUTPUT_CHANNEL.appendLine(msg);
            window.showErrorMessage(msg);
            feedbackRobocorpCodeError("INIT_NO_RCC_DIAGNOSTICS_2");
            return undefined;
        }
        if (rccDiagnostics.isRobocorpHomeOk()) {
            OUTPUT_CHANNEL.appendLine("Selected ROBOCORP_HOME: " + robocorpHome);
            let config = workspace.getConfiguration("robocorp");
            await config.update("home", robocorpHome, ConfigurationTarget.Global);
        }
    }

    function createOpenUrl(failedCheck) {
        return (value) => {
            if (value == "Open troubleshoot URL") {
                env.openExternal(Uri.parse(failedCheck.url));
            }
        };
    }
    let canProceed: boolean = true;
    for (const failedCheck of rccDiagnostics.failedChecks) {
        if (failedCheck.status == STATUS_FATAL) {
            canProceed = false;
        }
        let func = window.showErrorMessage;
        if (failedCheck.status == STATUS_WARNING) {
            func = window.showWarningMessage;
        }
        if (failedCheck.url) {
            func(failedCheck.message, "Open troubleshoot URL").then(createOpenUrl(failedCheck));
        } else {
            func(failedCheck.message);
        }
    }
    if (!canProceed) {
        feedbackRobocorpCodeError("INIT_RCC_STATUS_FATAL");
        return undefined;
    }

    progress.report({ message: "Update env (may take a few minutes)." });
    // Get information on a base package with our basic dependencies (this can take a while...).
    let rccEnvPromise = collectBaseEnv(robotConda, robocorpHome, rccDiagnostics);
    let timing = new Timing();

    let finishedCondaRun = false;
    let onFinish = function () {
        finishedCondaRun = true;
    };
    rccEnvPromise.then(onFinish, onFinish);

    // Busy async loop so that we can show the elapsed time.
    while (true) {
        await sleep(93); // Strange sleep so it's not always a .0 when showing ;)
        if (finishedCondaRun) {
            break;
        }
        if (timing.elapsedFromLastMeasurement(5000)) {
            progress.report({
                message: "Update env (may take a few minutes). " + timing.getTotalElapsedAsStr() + " elapsed.",
            });
        }
    }
    let envResult = await rccEnvPromise;
    OUTPUT_CHANNEL.appendLine("Took: " + timing.getTotalElapsedAsStr() + " to update conda env.");

    if (!envResult) {
        OUTPUT_CHANNEL.appendLine("Error creating conda env.");
        feedbackRobocorpCodeError("INIT_ERROR_CONDA_ENV");
        return undefined;
    }
    // Ok, we now have the holotree space created and just collected the environment variables. Let's now do
    // a raw python run with that information to collect information from python.

    let pythonExe = envResult.env["PYTHON_EXE"];
    if (!pythonExe) {
        OUTPUT_CHANNEL.appendLine("Error: PYTHON_EXE not available in the holotree environment.");
        feedbackRobocorpCodeError("INIT_NO_PYTHON_EXE_IN_HOLOTREE");
        return undefined;
    }

    let pythonTiming = new Timing();
    let resultPromise: Promise<ExecFileReturn> = execFilePromise(pythonExe, [getEnvInfoPy], { env: envResult.env });

    let finishedPythonRun = false;
    let onFinishPython = function () {
        finishedPythonRun = true;
    };
    resultPromise.then(onFinishPython, onFinishPython);

    // Busy async loop so that we can show the elapsed time.
    while (true) {
        await sleep(93); // Strange sleep so it's not always a .0 when showing ;)
        if (finishedPythonRun) {
            break;
        }
        if (timing.elapsedFromLastMeasurement(5000)) {
            progress.report({ message: "Collecting env info. " + timing.getTotalElapsedAsStr() + " elapsed." });
        }
    }
    let ret = await resultPromise;
    OUTPUT_CHANNEL.appendLine("Took: " + pythonTiming.getTotalElapsedAsStr() + " to collect python info.");
    return ret;
}

export async function getLanguageServerPythonInfoUncached(): Promise<InterpreterInfo | undefined> {
    let robotYaml = getExtensionRelativeFile("../../bin/create_env/robot.yaml");
    if (!robotYaml) {
        OUTPUT_CHANNEL.appendLine("Unable to find: ../../bin/create_env/robot.yaml in extension.");
        feedbackRobocorpCodeError("INIT_ROBOT_YAML_NOT_AVAILABLE");
        return;
    }

    let result: ExecFileReturn | undefined = await window.withProgress(
        {
            location: ProgressLocation.Notification,
            title: "Robocorp",
            cancellable: false,
        },
        createDefaultEnv
    );

    function disabled(msg: string): undefined {
        msg = "Robocorp Code extension disabled. Reason: " + msg;
        OUTPUT_CHANNEL.appendLine(msg);
        window.showErrorMessage(msg);
        OUTPUT_CHANNEL.show();
        return undefined;
    }

    if (!result) {
        feedbackRobocorpCodeError("INIT_NO_PYTHON_LANGUAGE_SERVER");
        return disabled("Unable to get python to launch language server.");
    }
    try {
        let jsonContents = result.stderr;
        let start: number = jsonContents.indexOf("JSON START>>");
        let end: number = jsonContents.indexOf("<<JSON END");
        if (start == -1 || end == -1) {
            feedbackRobocorpCodeError("INIT_NO_JSON_START_END");
            throw Error("Unable to find JSON START>> or <<JSON END");
        }
        start += "JSON START>>".length;
        jsonContents = jsonContents.substr(start, end - start);
        let contents: object = JSON.parse(jsonContents);
        let pythonExe = contents["python_executable"];
        OUTPUT_CHANNEL.appendLine("Python executable: " + pythonExe);
        OUTPUT_CHANNEL.appendLine("Python version: " + contents["python_version"]);
        OUTPUT_CHANNEL.appendLine("Robot Version: " + contents["robot_version"]);
        let env = contents["environment"];
        if (!env) {
            OUTPUT_CHANNEL.appendLine("Environment: NOT received");
        } else {
            // Print some env vars we may care about:
            OUTPUT_CHANNEL.appendLine("Environment:");
            OUTPUT_CHANNEL.appendLine("    PYTHONPATH: " + env["PYTHONPATH"]);
            OUTPUT_CHANNEL.appendLine("    APPDATA: " + env["APPDATA"]);
            OUTPUT_CHANNEL.appendLine("    HOMEDRIVE: " + env["HOMEDRIVE"]);
            OUTPUT_CHANNEL.appendLine("    HOMEPATH: " + env["HOMEPATH"]);
            OUTPUT_CHANNEL.appendLine("    HOME: " + env["HOME"]);
            OUTPUT_CHANNEL.appendLine("    ROBOT_ROOT: " + env["ROBOT_ROOT"]);
            OUTPUT_CHANNEL.appendLine("    ROBOT_ARTIFACTS: " + env["ROBOT_ARTIFACTS"]);
            OUTPUT_CHANNEL.appendLine("    RCC_INSTALLATION_ID: " + env["RCC_INSTALLATION_ID"]);
            OUTPUT_CHANNEL.appendLine("    ROBOCORP_HOME: " + env["ROBOCORP_HOME"]);
            OUTPUT_CHANNEL.appendLine("    PROCESSOR_ARCHITECTURE: " + env["PROCESSOR_ARCHITECTURE"]);
            OUTPUT_CHANNEL.appendLine("    OS: " + env["OS"]);
            OUTPUT_CHANNEL.appendLine("    PATH: " + env["PATH"]);
        }
        if (verifyFileExists(pythonExe)) {
            return {
                pythonExe: pythonExe,
                environ: contents["environment"],
                additionalPythonpathEntries: [],
            };
        }
        feedbackRobocorpCodeError("INIT_PYTHON_LS_DOES_NOT_EXIST");
        return disabled("Python executable: " + pythonExe + " does not exist.");
    } catch (error) {
        feedbackRobocorpCodeError("INIT_UNEXPECTED");
        return disabled(
            "Unable to get python to launch language server.\nStderr: " +
                result.stderr +
                "\nStdout (json contents): " +
                result.stdout
        );
    }
}
