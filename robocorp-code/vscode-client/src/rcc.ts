import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { XHRResponse, configure as configureXHR, xhr } from './requestLight';
import { getExtensionRelativeFile } from './files';
import { workspace, window, ProgressLocation, CancellationToken, Progress, extensions } from 'vscode';
import { OUTPUT_CHANNEL } from './channel';
import { Timing, sleep } from './time';
import { execFilePromise, ExecFileReturn } from './subprocess';

async function downloadRcc(progress: Progress<{ message?: string; increment?: number }>, token: CancellationToken): Promise<string | undefined> {

    // Configure library with http settings.
    // i.e.: https://code.visualstudio.com/docs/setup/network
    let httpSettings = workspace.getConfiguration('http');
    configureXHR(httpSettings.get<string>('proxy'), httpSettings.get<boolean>('proxyStrictSSL'));
    let location = getExpectedRccLocation();
    let relativePath: string;
    if (process.platform == 'win32') {
        if (process.arch === 'x64' || process.env.hasOwnProperty('PROCESSOR_ARCHITEW6432')) {
            // Check if node is a 64 bit process or if it's a 32 bit process running in a 64 bit processor.
            relativePath = '/windows64/rcc.exe';
        } else {
            // Do we even have a way to test a 32 bit build?
            relativePath = '/windows32/rcc.exe';

        }
    } else if (process.platform == 'darwin') {
        relativePath = '/macos64/rcc';

    } else {
        // Linux
        if (process.arch === 'x64') {
            relativePath = '/linux64/rcc';
        } else {
            relativePath = '/linux32/rcc';
        }
    }
    const RCC_VERSION = "v9.4.3";
    const prefix = "https://downloads.robocorp.com/rcc/releases/" + RCC_VERSION;
    const url: string = prefix + relativePath;

    // Downloads can go wrong (so, retry a few times before giving up).
    const maxTries = 3;
    let timing: Timing = new Timing();


    OUTPUT_CHANNEL.appendLine('Downloading rcc from: ' + url);
    for (let i = 0; i < maxTries; i++) {

        function onProgress(currLen: number, totalLen: number) {
            if (timing.elapsedFromLastMeasurement(300) || currLen == totalLen) {
                currLen /= (1024 * 1024);
                totalLen /= (1024 * 1024);
                let currProgress = currLen / totalLen * 100;
                let msg: string = 'Downloaded: ' + currLen.toFixed(1) + "MB of " + totalLen.toFixed(1) + "MB (" + currProgress.toFixed(1) + '%)';
                if (i > 0) {
                    msg = "Attempt: " + (i + 1) + " - " + msg;
                }
                progress.report({ message: msg });
                OUTPUT_CHANNEL.appendLine(msg);
            }
        }

        try {
            let response: XHRResponse = await xhr({
                'url': url,
                'onProgress': onProgress,
            });
            if (response.status == 200) {
                // Ok, we've been able to get it.
                // Note: only write to file after we get all contents to avoid
                // having partial downloads.
                OUTPUT_CHANNEL.appendLine('Finished downloading in: ' + timing.getTotalElapsedAsStr());
                OUTPUT_CHANNEL.appendLine('Writing to: ' + location);
                progress.report({ message: 'Finished downloading (writing to file).' });
                let s = fs.createWriteStream(location, { 'encoding': 'binary', 'mode': 0o744 });
                try {
                    response.responseData.forEach(element => {
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
                throw Error('Unable to download from ' + url + '. Response status: ' + response.status + 'Response message: ' + response.responseText);
            }
        } catch (error) {
            OUTPUT_CHANNEL.appendLine('Error downloading (' + i + ' of ' + maxTries + '). Error: ' + error);
            if (i == maxTries - 1) {
                return undefined;
            }
        }
    }
}

function getExpectedRccLocation(): string {
    let location: string;
    if (process.platform == 'win32') {
        location = getExtensionRelativeFile('../../bin/rcc.exe', false);
    } else {
        location = getExtensionRelativeFile('../../bin/rcc', false);
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
        await window.withProgress({
            location: ProgressLocation.Notification,
            title: "Download conda manager (rcc).",
            cancellable: false
        }, downloadRcc);
    }
    return location;

}

export async function submitIssueUI(logPath: string) {
    // Collect the issue information and send it using RCC.
    let name: string = await window.showInputBox({
        'prompt': 'Please provide your name for the issue report',
        'ignoreFocusOut': true,
    });
    if (!name) {
        return;
    }
    let email: string = await window.showInputBox({
        'prompt': 'Please provide your e-mail for the issue report',
        'ignoreFocusOut': true,
    });
    if (!email) {
        return;
    }
    let issueDescription: string = await window.showInputBox({
        'prompt': 'Please provide a brief description of the issue',
        'ignoreFocusOut': true,
    });
    if (!issueDescription) {
        return;
    }
    await submitIssue(
        logPath,
        "N/A",
        email,
        "N/A",
        "N/A",
        issueDescription,
    )
}

export const STATUS_OK = 'ok'
export const STATUS_FATAL = 'fatal'
export const STATUS_FAIL = 'fail'
export const STATUS_WARNING = 'warning'

export interface CheckDiagnostic {
    type: string
    status: string // ok | fatal | fail | warning
    message: string
    url: string
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
                if (check.type == 'RPA' && check.message.indexOf('ROBOCORP_HOME') != -1) {
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
export async function runConfigDiagnostics(rccLocation: string, robocorpHome: string | undefined): Promise<RCCDiagnostics | undefined> {
    try {
        let env = { ...process.env };
        if (robocorpHome) {
            env['ROBOCORP_HOME'] = robocorpHome;
        }
        let configureLongpathsOutput: ExecFileReturn = await execFilePromise(
            rccLocation, ['configure', 'diagnostics', '-j'],
            { env: env },
        );
        OUTPUT_CHANNEL.appendLine('RCC Diagnostics:\nStdout:\n' + configureLongpathsOutput.stdout + '\nStderr:\n' + configureLongpathsOutput.stderr);
        let outputAsJSON = JSON.parse(configureLongpathsOutput.stdout);
        let checks: CheckDiagnostic[] = outputAsJSON.checks;
        return new RCCDiagnostics(checks);
    } catch (error) {
        OUTPUT_CHANNEL.appendLine('Error getting RCC diagnostics: ' + error);
        return undefined;
    }
}

export async function submitIssue(
    logPath: string,
    dialogMessage: string,
    email: string,
    errorName: string,
    errorCode: string,
    errorMessage: string,
): Promise<undefined> {
    let errored: boolean = false;
    try {
        let rccLocation: string | undefined = await getRccLocation();
        if (rccLocation) {
            if (!fs.existsSync(rccLocation)) {
                OUTPUT_CHANNEL.appendLine('Unable to send issue report (' + rccLocation + ') does not exist.')
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
            OUTPUT_CHANNEL.appendLine('Log path: ' + logsRootDir);
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


            let version = extensions.getExtension('robocorp.robocorp-code').packageJSON.version;
            const metadata = {
                logsRootDir,
                platform: os.platform(),
                osRelease: os.release(),
                nodeVersion: process.version,
                version: version,
                controller: 'rcc.robocorpcode',
                dialogMessage,
                email,
                errorName,
                errorCode,
                errorMessage,
            };
            const reportPath: string = path.join(os.tmpdir(), `robocode_issue_report_${Date.now()}.json`);
            fs.writeFileSync(reportPath, JSON.stringify(metadata, null, 4), { encoding: 'utf-8' });
            let args: string[] = ['feedback', 'issue', '-r', reportPath, '--controller', 'RobocorpCode'];
            for (const file of logFiles) {
                args.push('-a');
                args.push(file);
            }
            await execFilePromise(rccLocation, args, {});
        }
    } catch (err) {
        errored = true;
        OUTPUT_CHANNEL.appendLine('Error sending issue: ' + err);
    }
    if (!errored) {
        OUTPUT_CHANNEL.appendLine('Issue sent.');
    }
    return;
}