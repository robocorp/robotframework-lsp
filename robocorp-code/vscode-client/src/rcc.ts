import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import * as crypto from "crypto";
import * as pathModule from "path";
import { XHRResponse, configure as configureXHR, xhr } from "./requestLight";
import { fileExists, getExtensionRelativeFile } from "./files";
import { workspace, window, ProgressLocation, CancellationToken, Progress, extensions } from "vscode";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { Timing, sleep } from "./time";
import { execFilePromise, ExecFileReturn } from "./subprocess";

function createBaseEnv(robocorpHome: string): { [key: string]: string | null } {
    let env: { [key: string]: string | null } = {};
    if (process.platform == "win32") {
        Object.keys(process.env).forEach(function (key) {
            // We could have something as `Path` -- convert it to `PATH`.
            env[key.toUpperCase()] = process.env[key];
        });
    } else {
        env = { ...process.env };
    }

    if (robocorpHome) {
        env["ROBOCORP_HOME"] = robocorpHome;
    }
    return env;
}

function envArrayToEnvMap(envArray: [], robocorpHome: string): { [key: string]: string | null } {
    let env = createBaseEnv(robocorpHome);
    for (let index = 0; index < envArray.length; index++) {
        const element = envArray[index];
        let key: string = element["key"];
        if (process.platform == "win32") {
            key = key.toUpperCase();
        }
        env[key] = element["value"];
    }
    return env;
}

async function checkCachedEnvValid(env): Promise<boolean> {
    let pythonExe = env["PYTHON_EXE"];

    if (!pythonExe || !fs.existsSync(pythonExe)) {
        OUTPUT_CHANNEL.appendLine("Error. PYTHON_EXE not valid in env cache.");
        return false;
    }
    let condaPrefix = env["CONDA_PREFIX"];
    if (!condaPrefix || !fs.existsSync(condaPrefix)) {
        OUTPUT_CHANNEL.appendLine("Error. CONDA_PREFIX not valid in env cache.");
        return false;
    }
    let condaPrefixIdentityYaml = path.join(condaPrefix, "identity.yaml");
    if (!fs.existsSync(condaPrefixIdentityYaml)) {
        OUTPUT_CHANNEL.appendLine("Error. " + condaPrefixIdentityYaml + " no longer exists.");
        return false;
    }

    let execFileReturn: ExecFileReturn = await execFilePromise(pythonExe, ["-c", 'import threading;print("OK")'], {
        env: env,
    });
    if (execFileReturn.stderr) {
        OUTPUT_CHANNEL.appendLine(
            "Expected no output in stderr from cached python (" + pythonExe + "). Found:\n" + execFileReturn.stderr
        );
        return false;
    }
    if (!execFileReturn.stdout) {
        OUTPUT_CHANNEL.appendLine("No output received when checking cached python (" + pythonExe + ").");
        return false;
    }
    if (!execFileReturn.stdout.includes("OK")) {
        OUTPUT_CHANNEL.appendLine(
            "Expected 'OK' in output from cached python (" + pythonExe + "). Found:\n" + execFileReturn.stdout
        );
        return false;
    }
    return true;
}

async function downloadRcc(
    progress: Progress<{ message?: string; increment?: number }>,
    token: CancellationToken
): Promise<string | undefined> {
    // Configure library with http settings.
    // i.e.: https://code.visualstudio.com/docs/setup/network
    let httpSettings = workspace.getConfiguration("http");
    configureXHR(httpSettings.get<string>("proxy"), httpSettings.get<boolean>("proxyStrictSSL"));
    let location = getExpectedRccLocation();
    let relativePath: string;
    if (process.platform == "win32") {
        if (process.arch === "x64" || process.env.hasOwnProperty("PROCESSOR_ARCHITEW6432")) {
            // Check if node is a 64 bit process or if it's a 32 bit process running in a 64 bit processor.
            relativePath = "/windows64/rcc.exe";
        } else {
            // Do we even have a way to test a 32 bit build?
            relativePath = "/windows32/rcc.exe";
        }
    } else if (process.platform == "darwin") {
        relativePath = "/macos64/rcc";
    } else {
        // Linux
        if (process.arch === "x64") {
            relativePath = "/linux64/rcc";
        } else {
            relativePath = "/linux32/rcc";
        }
    }
    const RCC_VERSION = "v11.2.0";
    const prefix = "https://downloads.robocorp.com/rcc/releases/" + RCC_VERSION;
    const url: string = prefix + relativePath;

    // Downloads can go wrong (so, retry a few times before giving up).
    const maxTries = 3;
    let timing: Timing = new Timing();

    OUTPUT_CHANNEL.appendLine("Downloading rcc from: " + url);
    for (let i = 0; i < maxTries; i++) {
        function onProgress(currLen: number, totalLen: number) {
            if (timing.elapsedFromLastMeasurement(300) || currLen == totalLen) {
                currLen /= 1024 * 1024;
                totalLen /= 1024 * 1024;
                let currProgress = (currLen / totalLen) * 100;
                let msg: string =
                    "Downloaded: " +
                    currLen.toFixed(1) +
                    "MB of " +
                    totalLen.toFixed(1) +
                    "MB (" +
                    currProgress.toFixed(1) +
                    "%)";
                if (i > 0) {
                    msg = "Attempt: " + (i + 1) + " - " + msg;
                }
                progress.report({ message: msg });
                OUTPUT_CHANNEL.appendLine(msg);
            }
        }

        try {
            let response: XHRResponse = await xhr({
                "url": url,
                "onProgress": onProgress,
            });
            if (response.status == 200) {
                // Ok, we've been able to get it.
                // Note: only write to file after we get all contents to avoid
                // having partial downloads.
                OUTPUT_CHANNEL.appendLine("Finished downloading in: " + timing.getTotalElapsedAsStr());
                OUTPUT_CHANNEL.appendLine("Writing to: " + location);
                progress.report({ message: "Finished downloading (writing to file)." });
                let s = fs.createWriteStream(location, { "encoding": "binary", "mode": 0o744 });
                try {
                    response.responseData.forEach((element) => {
                        s.write(element);
                    });
                } finally {
                    s.close();
                }

                // If we don't sleep after downloading, the first activation seems to fail on Windows and Mac
                // (EBUSY on Windows, undefined on Mac).
                await sleep(200);

                return location;
            } else {
                throw Error(
                    "Unable to download from " +
                        url +
                        ". Response status: " +
                        response.status +
                        "Response message: " +
                        response.responseText
                );
            }
        } catch (error) {
            OUTPUT_CHANNEL.appendLine("Error downloading (" + i + " of " + maxTries + "). Error: " + error.message);
            if (i == maxTries - 1) {
                return undefined;
            }
        }
    }
}

function getExpectedRccLocation(): string {
    let location: string;
    if (process.platform == "win32") {
        location = getExtensionRelativeFile("../../bin/rcc.exe", false);
    } else {
        location = getExtensionRelativeFile("../../bin/rcc", false);
    }
    return location;
}

// We can't really ship rcc per-platform right now (so, we need to either
// download it or ship it along).
// See: https://github.com/microsoft/vscode/issues/6929
// See: https://github.com/microsoft/vscode/issues/23251
// In particular, if we download things, we should use:
// https://www.npmjs.com/package/request-light according to:
// https://github.com/microsoft/vscode/issues/6929#issuecomment-222153748

export async function getRccLocation(): Promise<string | undefined> {
    let location = getExpectedRccLocation();
    if (!fs.existsSync(location)) {
        await window.withProgress(
            {
                location: ProgressLocation.Notification,
                title: "Download conda manager (rcc).",
                cancellable: false,
            },
            downloadRcc
        );
    }
    return location;
}

export async function submitIssueUI(logPath: string) {
    // Collect the issue information and send it using RCC.
    let email: string;
    let askEmailMsg: string = "Please provide your e-mail for the issue report";
    do {
        email = await window.showInputBox({
            "prompt": askEmailMsg,
            "ignoreFocusOut": true,
        });
        if (!email) {
            return;
        }
        // if it doesn't have an @, ask again
        askEmailMsg = "Invalid e-mail provided. Please provide your e-mail for the issue report";
    } while (email.indexOf("@") == -1);

    let issueDescription: string = await window.showInputBox({
        "prompt": "Please provide a brief description of the issue",
        "ignoreFocusOut": true,
    });
    if (!issueDescription) {
        return;
    }
    await submitIssue(logPath, "Robocorp Code", email, "Robocorp Code", "Robocorp Code", issueDescription);
}

export const STATUS_OK = "ok";
export const STATUS_FATAL = "fatal";
export const STATUS_FAIL = "fail";
export const STATUS_WARNING = "warning";

export interface CheckDiagnostic {
    type: string;
    status: string; // ok | fatal | fail | warning
    message: string;
    url: string;
}

export class RCCDiagnostics {
    failedChecks: CheckDiagnostic[];
    private roboHomeOk: boolean;

    constructor(checks: CheckDiagnostic[]) {
        this.roboHomeOk = true;
        this.failedChecks = [];

        for (const check of checks) {
            if (check.status != STATUS_OK) {
                this.failedChecks.push(check);
                if (check.type == "RPA" && check.message.indexOf("ROBOCORP_HOME") != -1) {
                    this.roboHomeOk = false;
                }
            }
        }
    }

    isRobocorpHomeOk(): boolean {
        return this.roboHomeOk;
    }
}

/**
 * @param robocorpHome if given, this will be passed as the ROBOCORP_HOME environment variable.
 */
export async function runConfigDiagnostics(
    rccLocation: string,
    robocorpHome: string | undefined
): Promise<RCCDiagnostics | undefined> {
    try {
        let timing = new Timing();
        let env = { ...process.env };
        if (robocorpHome) {
            env["ROBOCORP_HOME"] = robocorpHome;
        }
        let configureLongpathsOutput: ExecFileReturn = await execFilePromise(
            rccLocation,
            ["configure", "diagnostics", "-j", "--controller", "RobocorpCode"],
            { env: env }
        );
        OUTPUT_CHANNEL.appendLine(
            "RCC Diagnostics:" +
                "\nStdout:\n" +
                configureLongpathsOutput.stdout +
                "\nStderr:\n" +
                configureLongpathsOutput.stderr +
                "\nTook " +
                timing.getTotalElapsedAsStr() +
                " to obtain diagnostics."
        );

        let outputAsJSON = JSON.parse(configureLongpathsOutput.stdout);
        let checks: CheckDiagnostic[] = outputAsJSON.checks;
        return new RCCDiagnostics(checks);
    } catch (error) {
        logError("Error getting RCC diagnostics.", error);
        return undefined;
    }
}

export async function submitIssue(
    logPath: string,
    dialogMessage: string,
    email: string,
    errorName: string,
    errorCode: string,
    errorMessage: string
): Promise<undefined> {
    let errored: boolean = false;
    try {
        let rccLocation: string | undefined = await getRccLocation();
        if (rccLocation) {
            if (!fs.existsSync(rccLocation)) {
                OUTPUT_CHANNEL.appendLine("Unable to send issue report (" + rccLocation + ") does not exist.");
                return;
            }

            function acceptLogFile(f: string): boolean {
                let lower = path.basename(f).toLowerCase();
                if (!lower.endsWith(".log")) {
                    return false;
                }
                // Whitelist what we want so that we don't gather unwanted info.
                if (lower.includes("robocorp code") || lower.includes("robot framework") || lower.includes("exthost")) {
                    return true;
                }
                return false;
            }

            // This should be parent directory for the logs.
            let logsRootDir: string = path.dirname(logPath);
            OUTPUT_CHANNEL.appendLine("Log path: " + logsRootDir);
            let logFiles: string[] = [];

            const stat = await fs.promises.stat(logsRootDir);
            if (stat.isDirectory()) {
                // Get the .log files under the logsRootDir and subfolders.
                const files: string[] = await fs.promises.readdir(logsRootDir);
                for (const fileI of files) {
                    let f: string = path.join(logsRootDir, fileI);
                    const stat = await fs.promises.stat(f);
                    if (acceptLogFile(f) && stat.isFile()) {
                        logFiles.push(f);
                    } else if (stat.isDirectory()) {
                        // No need to recurse (we just go 1 level deep).
                        let currDir: string = f;
                        const innerFiles: string[] = await fs.promises.readdir(currDir);
                        for (const fileI of innerFiles) {
                            let f: string = path.join(currDir, fileI);
                            const stat = await fs.promises.stat(f);
                            if (acceptLogFile(f) && stat.isFile()) {
                                logFiles.push(f);
                            }
                        }
                    }
                }
            }

            let version = extensions.getExtension("robocorp.robocorp-code").packageJSON.version;
            const metadata = {
                logsRootDir,
                platform: os.platform(),
                osRelease: os.release(),
                nodeVersion: process.version,
                version: version,
                controller: "rcc.robocorpcode",
                dialogMessage,
                email,
                errorName,
                errorCode,
                errorMessage,
            };
            const reportPath: string = path.join(os.tmpdir(), `robocode_issue_report_${Date.now()}.json`);
            fs.writeFileSync(reportPath, JSON.stringify(metadata, null, 4), { encoding: "utf-8" });
            let args: string[] = ["feedback", "issue", "-r", reportPath, "--controller", "RobocorpCode"];
            for (const file of logFiles) {
                args.push("-a");
                args.push(file);
            }
            await execFilePromise(rccLocation, args, {});
        }
    } catch (err) {
        errored = true;
        logError("Error sending issue.", err);
    }
    if (!errored) {
        OUTPUT_CHANNEL.appendLine("Issue sent.");
    }
    return;
}

interface IEnvInfo {
    env: { [key: string]: string | null };
    robocorpHome: string | undefined;
    rccLocation: string;
}

/**
 * This function creates the base holotree space with RCC and then returns its info
 * to start up the language server.
 *
 * @param robocorpHome usually roboConfig.getHome()
 */
export async function collectBaseEnv(
    condaFilePath: string,
    robocorpHome: string | undefined
): Promise<IEnvInfo | undefined> {
    const text: string = (await fs.promises.readFile(condaFilePath, "utf-8")).replace(/(?:\r\n|\r)/g, "\n");
    const hash = crypto.createHash("sha256").update(text, "utf8").digest("hex");
    let spaceName = "vscode-base-v01-" + hash.substring(0, 6);

    let robocorpCodePath = path.join(robocorpHome, ".robocorp_code");
    let spaceInfoPath = path.join(robocorpCodePath, spaceName);
    let rccEnvInfoCachePath = path.join(spaceInfoPath, "rcc_env_info.json");
    try {
        if (!fs.existsSync(spaceInfoPath)) {
            fs.mkdirSync(spaceInfoPath, { "recursive": true });
        }
    } catch (err) {
        logError("Error creating directory: " + spaceInfoPath, err);
    }

    const rccLocation = await getRccLocation();
    if (!rccLocation) {
        window.showErrorMessage("Unable to find RCC.");
        return;
    }

    // If the robot is located in a directory that has '/devdata/env.json', we must automatically
    // add the -e /path/to/devdata/env.json.

    let robotDirName = pathModule.dirname(condaFilePath);
    let envFilename = pathModule.join(robotDirName, "devdata", "env.json");
    let args = ["holotree", "variables", "--space", spaceName, "--json", condaFilePath];
    if (await fileExists(envFilename)) {
        args.push("-e");
        args.push(envFilename);
    }
    args.push("--controller");
    args.push("RobocorpCode");

    let envArray = undefined;
    try {
        if (fs.existsSync(rccEnvInfoCachePath)) {
            let contents = fs.readFileSync(rccEnvInfoCachePath, { "encoding": "utf-8" });
            envArray = JSON.parse(contents);
            let cachedEnv = envArrayToEnvMap(envArray, robocorpHome);
            try {
                // Ok, we have the python exe and the env seems valid. Let's make sure it actually works.
                let cachedPythonOk: boolean = await checkCachedEnvValid(cachedEnv);
                if (!cachedPythonOk) {
                    envArray = undefined;
                }
            } catch (error) {
                logError("Error: error verifying if env is still valid.", error);
                envArray = undefined;
            }

            if (envArray) {
                OUTPUT_CHANNEL.appendLine("Loading base environment from: " + rccEnvInfoCachePath);
            }
        }
    } catch (err) {
        logError("Unable to use cached environment info (recomputing)...", err);
        envArray = undefined;
    }

    // If the env array is undefined, compute it now and cache the info to be reused later.
    if (!envArray) {
        let execFileReturn: ExecFileReturn = await execFilePromise(rccLocation, args, {
            env: createBaseEnv(robocorpHome),
        });
        if (!execFileReturn.stdout) {
            OUTPUT_CHANNEL.appendLine("Error: Unable to collect environment from RCC.");
            return undefined;
        }
        try {
            envArray = JSON.parse(execFileReturn.stdout);
        } catch (error) {
            logError("Error parsing env from RCC: " + execFileReturn.stdout, error);
        }
        if (!envArray) {
            OUTPUT_CHANNEL.appendLine("Error: Unable to collect env array.");
            return undefined;
        }
        try {
            fs.writeFileSync(rccEnvInfoCachePath, JSON.stringify(envArray));
        } catch (err) {
            logError("Error writing environment cache.", err);
        }
    }

    let timestampPath = path.join(spaceInfoPath, "last_usage");
    try {
        fs.writeFileSync(timestampPath, "" + Date.now());
    } catch (err) {
        logError("Error writing last usage time to: " + timestampPath, err);
    }

    let finalEnv: { [key: string]: string | null } = envArrayToEnvMap(envArray, robocorpHome);
    let tempDir = finalEnv["TEMP"];
    if (tempDir) {
        try {
            // Try to remove the file related to recycling this dir (we don't want to
            // recycle the TEMP dir of this particular env).
            fs.unlink(path.join(tempDir, "recycle.now"), (err) => {});
        } catch (err) {}
        try {
            // Create the temp dir (if not there)
            fs.mkdir(tempDir, { "recursive": true }, (err) => {});
        } catch (err) {}
    }

    return { "env": finalEnv, "robocorpHome": robocorpHome, "rccLocation": rccLocation };
}
