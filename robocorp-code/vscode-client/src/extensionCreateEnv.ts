"use strict";

import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";

import { workspace, window, Progress, ProgressLocation, ConfigurationTarget, env, Uri } from "vscode";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { fileExists, getExtensionRelativeFile, makeDirs, verifyFileExists } from "./files";
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
import { ActionResult, InterpreterInfo } from "./protocols";
import { join } from "path";
import { GLOBAL_STATE } from "./extension";

async function resolveDrive(driveLetter: string): Promise<string | undefined> {
    const output = await execFilePromise(
        "subst.exe",
        [],
        { shell: true },
        { hideCommandLine: true, showOutputInteractively: false }
    );
    const stdout = output.stdout;
    driveLetter = driveLetter.toUpperCase();
    for (const line of stdout.split(/\r?\n/)) {
        const splitted = line.split("=>");
        if (splitted.length === 2) {
            const drivepart = splitted[0].trim();
            const resolvepart = splitted[1].trim();
            if (drivepart.endsWith(":\\:") && drivepart[1] == ":") {
                if (drivepart[0].toUpperCase() === driveLetter) {
                    OUTPUT_CHANNEL.appendLine(`Resolved substed drive: ${driveLetter} to ${resolvepart}.`);
                    return resolvepart;
                }
            }
        }
    }
    return undefined;
}

export async function runAsAdminWin32(rccLocation: string, args: string[], env) {
    try {
        // Now, at this point we resolve the links to have a canonical location, because
        // we'll execute with a different user (i.e.: admin), we first resolve substs
        // which may not be available for that user (i.e.: a subst can be applied to one
        // account and not to the other) because path.resolve and fs.realPathSync don't
        // seem to resolve substed drives, we do it manually here.

        if (rccLocation.charAt(1) == ":") {
            // Check that we actually have a drive there.
            let resolved: string | undefined = undefined;
            try {
                // Note: this used to work for me (on Windows 10/some version of VSCode),
                // but it seems be failing now, so, another workaround is done to read
                // the drive mappings using subst directly.
                resolved = fs.readlinkSync(rccLocation.charAt(0) + ":");
            } catch (error) {
                // ignore (maybe it's not a link)
                try {
                    resolved = await resolveDrive(rccLocation.charAt(0));
                } catch (error) {
                    // ignore
                }
            }

            if (resolved) {
                rccLocation = path.join(resolved, rccLocation.slice(2));
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
            await runAsAdminWin32(rccLocation, ["configure", "longpaths", "--enable"], { ...process.env });
            // Wait a second for the command to be executed as admin before proceeding.
            await sleep(1000);
        }
    } catch (error) {
        // Ignore here...
    }
}

async function isLongPathSupportEnabledOnWindows(rccLocation: string, robocorpHome: string): Promise<boolean> {
    try {
        await makeDirs(robocorpHome);
        const initialTarget = join(robocorpHome, "longpath_" + Date.now());
        let target = initialTarget;

        for (let i = 0; target.length < 270; i++) {
            target = join(target, "subdirectory" + i);
        }
        // await makeDirs(target); -- this seems to always work (applications can be built
        // with a manifest to support longpaths, which is apparently done by node, so,
        // check using cmd /c mkdir).
        const args = ["/c", "mkdir", target];
        let enabled = false;
        try {
            await execFilePromise(
                "cmd.exe",
                args,
                { shell: false },
                { hideCommandLine: true, showOutputInteractively: false }
            );
            enabled = await fileExists(target);
        } catch (err) {
            // Ignore
        }

        try {
            // Don't wait for async.
            // Note: remove even if not found as it may've created it partially.
            fs.rm(initialTarget, { recursive: true, force: true, maxRetries: 1 }, () => {});
        } catch (error) {
            // Ignore error
        }
        OUTPUT_CHANNEL.appendLine("Windows long paths support enabled");
        return enabled;
    } catch (error) {
        OUTPUT_CHANNEL.appendLine("Windows long paths support not enabled. Error: " + error.message);
        return false;
    }

    // Code which used to use RCC (not using it because it could error if using diagnostics at the same time.
    // See: https://github.com/robocorp/rcc/issues/45).
    // let enabled: boolean = true;
    // let stdout = "<not collected>";
    // let stderr = "<not collected>";
    // try {
    //     let configureLongpathsOutput: ExecFileReturn = await execFilePromise(rccLocation, ["configure", "longpaths"], {
    //         env: { ...process.env },
    //     });
    //     stdout = configureLongpathsOutput.stdout;
    //     stderr = configureLongpathsOutput.stderr;
    //     if (stdout.indexOf("OK.") != -1 || stderr.indexOf("OK.") != -1) {
    //         enabled = true;
    //     } else {
    //         enabled = false;
    //     }
    // } catch (error) {
    //     enabled = false;
    //     logError("There was some error with rcc configure longpaths.", error, "RCC_CONFIGURE_LONGPATHS");
    // }
    // if (enabled) {
    //     OUTPUT_CHANNEL.appendLine("Windows long paths support enabled");
    // } else {
    //     OUTPUT_CHANNEL.appendLine(
    //         `Windows long paths support NOT enabled.\nRCC stdout:\n${stdout}\nRCC stderr:\n${stderr}`
    //     );
    // }
    // return enabled;
}

async function verifyLongPathSupportOnWindows(
    rccLocation: string,
    robocorpHome: string,
    failsPreventStartup: boolean
): Promise<boolean> {
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

            let enabled: boolean = await isLongPathSupportEnabledOnWindows(rccLocation, robocorpHome);

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
                    let enabled = await isLongPathSupportEnabledOnWindows(rccLocation, robocorpHome);
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
                    if (failsPreventStartup) {
                        OUTPUT_CHANNEL.appendLine(
                            "Extension will not be activated because Windows long paths support not enabled."
                        );
                    } else {
                        OUTPUT_CHANNEL.appendLine("Windows long paths support not enabled.");
                    }
                    return false;
                }

                let resultOkLongPath = await window.showInformationMessage(
                    "Press Ok after Long Path support is manually enabled.",
                    { "modal": true },
                    "Ok"
                    // Auto-cancel in modal
                );
                if (!resultOkLongPath) {
                    if (failsPreventStartup) {
                        OUTPUT_CHANNEL.appendLine(
                            "Extension will not be activated because Windows long paths support not enabled."
                        );
                    } else {
                        OUTPUT_CHANNEL.appendLine("Windows long paths support not enabled.");
                    }
                    return false;
                }
            } else {
                return true;
            }
        }
    }
    return true;
}

export async function basicValidations(
    rccLocation: string,
    robocorpHome: string,
    configDiagnosticsPromise: Promise<RCCDiagnostics | undefined>,
    failsPreventStartup: boolean
): Promise<ActionResult<RCCDiagnostics>> {
    // Check that the user has long names enabled on windows.
    if (
        !(await verifyLongPathSupportOnWindows(rccLocation, robocorpHome, failsPreventStartup)) &&
        failsPreventStartup
    ) {
        feedbackRobocorpCodeError("INIT_NO_LONGPATH_SUPPORT");
        return { success: false, message: "", result: undefined };
    }

    // Check that ROBOCORP_HOME is valid (i.e.: doesn't have any spaces in it).
    let rccDiagnostics: RCCDiagnostics | undefined = await configDiagnosticsPromise;
    if (!rccDiagnostics) {
        let msg: string = "There was an error getting RCC diagnostics. Robocorp Code will not be started!";
        if (!failsPreventStartup) {
            msg = "There was an error getting RCC diagnostics.";
        }
        OUTPUT_CHANNEL.appendLine(msg);
        window.showErrorMessage(msg);
        feedbackRobocorpCodeError("INIT_NO_RCC_DIAGNOSTICS");
        return { success: false, message: "", result: rccDiagnostics };
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
            if (failsPreventStartup) {
                return { success: false, message: "", result: rccDiagnostics };
            } else {
                break;
            }
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
            if (failsPreventStartup) {
                return { success: false, message: "", result: rccDiagnostics };
            } else {
                break;
            }
        }
        if (uriResult.length != 1) {
            OUTPUT_CHANNEL.appendLine("Expected 1 path to set as ROBOCORP_HOME. Found: " + uriResult.length);
            feedbackRobocorpCodeError("INIT_ROBOCORP_HOME_NO_PATH");
            if (failsPreventStartup) {
                return { success: false, message: "", result: rccDiagnostics };
            } else {
                break;
            }
        }
        robocorpHome = uriResult[0].fsPath;
        rccDiagnostics = await runConfigDiagnostics(rccLocation, robocorpHome);
        if (!rccDiagnostics) {
            let msg: string = "There was an error getting RCC diagnostics. Robocorp Code will not be started!";
            if (!failsPreventStartup) {
                msg = "There was an error getting RCC diagnostics.";
            }
            OUTPUT_CHANNEL.appendLine(msg);
            window.showErrorMessage(msg);
            feedbackRobocorpCodeError("INIT_NO_RCC_DIAGNOSTICS_2");
            if (failsPreventStartup) {
                return { success: false, message: "", result: rccDiagnostics };
            } else {
                break;
            }
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
        return { success: false, message: "", result: rccDiagnostics };
    }

    return { success: true, message: "", result: rccDiagnostics };
}

/**
 * @returns the result of running `get_env_info.py`.
 */
async function createDefaultEnv(
    progress: Progress<{ message?: string; increment?: number }>,
    robotConda: string,
    robotCondaHash: string,
    rccLocation: string,
    robocorpHome: string,
    configDiagnosticsPromise: Promise<RCCDiagnostics | undefined>
): Promise<ExecFileReturn> | undefined {
    const getEnvInfoPy = getExtensionRelativeFile("../../bin/create_env/get_env_info.py");
    if (!getEnvInfoPy) {
        OUTPUT_CHANNEL.appendLine("Unable to find: ../../bin/create_env/get_env_info.py in extension.");
        feedbackRobocorpCodeError("INIT_GET_ENV_INFO_FAIL");
        return undefined;
    }

    const basicValidationsResult = await basicValidations(rccLocation, robocorpHome, configDiagnosticsPromise, true);
    if (!basicValidationsResult.success) {
        return undefined;
    }

    progress.report({ message: "Update env (may take a few minutes)." });
    // Get information on a base package with our basic dependencies (this can take a while...).
    const rccDiagnostics = basicValidationsResult.result;
    let rccEnvPromise = collectBaseEnv(robotConda, robotCondaHash, robocorpHome, rccDiagnostics);
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

/**
 * Shows a messages saying that the extension is disabled (as an error message to the user)
 * and logs it to OUTPUT > Robocorp Code.
 */
function disabled(msg: string): undefined {
    msg = "Robocorp Code extension disabled. Reason: " + msg;
    OUTPUT_CHANNEL.appendLine(msg);
    window.showErrorMessage(msg);
    OUTPUT_CHANNEL.show();
    return undefined;
}

/**
 * Helper class for making the startup.
 */
class StartupHelper {
    robotCondaHashPromise: Promise<string | undefined>;
    robotYaml: string | undefined;
    robotConda: string | undefined;

    feedbackErrorCode: string | undefined = undefined;
    feedbackErrorMessage: string | undefined = undefined;

    constructor() {
        this.robotYaml = getExtensionRelativeFile("../../bin/create_env/robot.yaml");
        if (!this.robotYaml) {
            this.error(
                "INIT_ROBOT_YAML_NOT_AVAILABLE",
                "Unable to find: ../../bin/create_env/robot.yaml in extension."
            );
            return;
        }

        switch (process.platform) {
            case "darwin":
                this.robotConda = getExtensionRelativeFile("../../bin/create_env/conda_vscode_darwin_amd64.yaml");
                break;
            case "linux":
                this.robotConda = getExtensionRelativeFile("../../bin/create_env/conda_vscode_linux_amd64.yaml");
                break;
            case "win32":
                this.robotConda = getExtensionRelativeFile("../../bin/create_env/conda_vscode_windows_amd64.yaml");
                break;
            default:
                this.robotConda = getExtensionRelativeFile("../../bin/create_env/conda.yaml");
                break;
        }

        if (!this.robotConda) {
            this.error(
                "INIT_CONDA_YAML_NOT_AVAILABLE",
                `Unable to find: conda.yaml for ${process.platform} in ../../bin/create_env/.`
            );
        }

        this.robotCondaHashPromise = (async (): Promise<string | undefined> => {
            try {
                const text: string = (await fs.promises.readFile(this.robotConda, "utf-8")).replace(
                    /(?:\r\n|\r)/g,
                    "\n"
                );
                return crypto.createHash("sha256").update(text, "utf8").digest("hex");
            } catch (error) {
                this.error("INIT_READ_CONDA_YAML", "Error reading: " + this.robotConda, error);
            }
            return undefined;
        })();
    }

    private error(errorCode: string, msg: string, error?: any) {
        this.feedbackErrorMessage = msg;
        this.feedbackErrorCode = errorCode;

        logError(msg, error, errorCode);
        disabled(this.feedbackErrorMessage);
    }

    hasStartupErrors(): boolean {
        return this.feedbackErrorMessage !== undefined || this.feedbackErrorCode !== undefined;
    }

    async getRobotCondaHash(): Promise<string | undefined> {
        return await this.robotCondaHashPromise;
    }
}

const CACHE_KEY_DEFAULT_ENV_JSON_CONTENTS = "DEFAULT_ENV_JSON_CONTENTS";
const CACHE_KEY_LAST_ROBOT_CONDA_HASH = "LAST_ROBOT_CONDA_HASH";
// This is set just when the language server is properly set (and it's reset at each new invocation).
export const CACHE_KEY_LAST_WORKED = "LAST_WORKED";

/**
 * Provides the python information needed to start the language server.
 */
export async function getLanguageServerPythonInfoUncached(): Promise<InterpreterInfo | undefined> {
    const getRccLocationPromise: Promise<string | undefined> = getRccLocation();

    const startupHelper = new StartupHelper();
    if (startupHelper.hasStartupErrors()) {
        return;
    }

    // Note: the startup helper notifies about errors in getRobotCondaHash already.
    let robotCondaHash: string | undefined = await startupHelper.getRobotCondaHash();
    if (!robotCondaHash) {
        return;
    }

    let rccLocation = await getRccLocationPromise;
    if (!rccLocation) {
        feedbackRobocorpCodeError("INIT_RCC_NOT_AVAILABLE");
        return disabled("Unable to get rcc executable location.");
    }

    let robocorpHome: string = await getRobocorpHome();
    const configDiagnosticsPromise: Promise<RCCDiagnostics | undefined> = runConfigDiagnostics(
        rccLocation,
        robocorpHome
    );

    // Get and clear flag (it's set to true when the language server successfully starts afterwards
    // -- if it doesn't we have to refresh the env again instead of using the cached version).
    const lastWorked = GLOBAL_STATE.get(CACHE_KEY_LAST_WORKED);
    GLOBAL_STATE.update(CACHE_KEY_LAST_WORKED, undefined);

    if (GLOBAL_STATE.get(CACHE_KEY_LAST_ROBOT_CONDA_HASH) === robotCondaHash && lastWorked) {
        const initialJsonContents: string | undefined = GLOBAL_STATE.get(CACHE_KEY_DEFAULT_ENV_JSON_CONTENTS);
        if (initialJsonContents !== undefined && initialJsonContents.length > 0) {
            const ret = extractInfoFromJsonContents(initialJsonContents);
            if (ret.success) {
                // If it worked, schedule the validation to be done later but return with the result right away!
                basicValidations(rccLocation, robocorpHome, configDiagnosticsPromise, false);
                return ret.result;
            }
            // Don't log anything if it didn't work (just stop using the cache).
        }
    }

    let stderr: string = "<not available>";
    let stdout: string = "<not available>";
    let result: ExecFileReturn | undefined = await window.withProgress(
        {
            location: ProgressLocation.Notification,
            title: "Robocorp",
            cancellable: false,
        },
        async (progress: Progress<{ message?: string; increment?: number }>): Promise<ExecFileReturn> | undefined => {
            return await createDefaultEnv(
                progress,
                startupHelper.robotConda,
                robotCondaHash,
                rccLocation,
                robocorpHome,
                configDiagnosticsPromise
            );
        }
    );

    if (!result) {
        feedbackRobocorpCodeError("INIT_NO_PYTHON_LANGUAGE_SERVER");
        return disabled("Unable to get python to launch language server.");
    }
    const initialJsonContents = result.stderr;
    stderr = result.stderr;
    stdout = result.stdout;

    try {
        if (initialJsonContents === undefined || initialJsonContents.length == 0) {
            feedbackRobocorpCodeError("INIT_PYTHON_NO_JSON_CONTENTS");
            return disabled("Unable to collect information for base environment (no json contents).");
        }
        const ret: ActionResult<InterpreterInfo> = extractInfoFromJsonContents(initialJsonContents);
        if (ret.success) {
            // If everything seems fine up to this point, cache it so that we can start
            // just by using it afterwards.
            GLOBAL_STATE.update(CACHE_KEY_DEFAULT_ENV_JSON_CONTENTS, initialJsonContents);
            GLOBAL_STATE.update(CACHE_KEY_LAST_ROBOT_CONDA_HASH, robotCondaHash);
            return ret.result;
        } else {
            feedbackRobocorpCodeError("INIT_PYTHON_BAD_JSON_CONTENTS");
            return disabled(ret.message);
        }
    } catch (error) {
        feedbackRobocorpCodeError("INIT_UNEXPECTED");
        return disabled("Unable to get python to launch language server.\nStderr: " + stderr + "\nStdout: " + stdout);
    }
}

function extractInfoFromJsonContents(initialJsonContents: string): ActionResult<InterpreterInfo> {
    let jsonContents: string = initialJsonContents;
    let start: number = jsonContents.indexOf("JSON START>>");
    let end: number = jsonContents.indexOf("<<JSON END");
    if (start == -1 || end == -1) {
        return {
            success: false,
            message: `Unable to start because JSON START or JSON END could not be found.`,
            result: undefined,
        };
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
            success: true,
            message: "",
            result: {
                pythonExe: pythonExe,
                environ: contents["environment"],
                additionalPythonpathEntries: [],
            },
        };
    }
    return {
        success: false,
        message: `Unable to start because ${pythonExe} does not exist.`,
        result: undefined,
    };
}
