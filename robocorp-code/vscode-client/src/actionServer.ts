import { getActionserverLocation, setActionserverLocation } from "./robocorpSettings";
import { fileExists, makeDirs } from "./files";
import { CancellationToken, Progress, ProgressLocation, Terminal, Uri, window, workspace } from "vscode";
import { createEnvWithRobocorpHome, download, getRobocorpHome } from "./rcc";
import path = require("path");
import { OUTPUT_CHANNEL, logError } from "./channel";
import * as http from "http";
import { listAndAskRobotSelection } from "./activities";
import { ExecFileReturn, execFilePromise } from "./subprocess";
import { compareVersions } from "./common";
import { showSelectOneStrQuickPick } from "./ask";
import { sleep } from "./time";

//Default: Linux
let DOWNLOAD_URL = "https://downloads.robocorp.com/action-server/releases/latest/linux64/action-server";
if (process.platform === "win32") {
    DOWNLOAD_URL = "https://downloads.robocorp.com/action-server/releases/latest/windows64/action-server.exe";
} else if (process.platform === "darwin") {
    DOWNLOAD_URL = "https://downloads.robocorp.com/action-server/releases/latest/macos64/action-server";
}

// Update so that Robocorp Code requests the latest version of the action server.
const LATEST_ACTION_SERVER_VERSION = "0.3.2";

async function downloadActionServer(internalActionServerLocation: string) {
    await window.withProgress(
        {
            location: ProgressLocation.Notification,
            title: "Downloading action server",
            cancellable: false,
        },
        async (
            progress: Progress<{ message?: string; increment?: number }>,
            token: CancellationToken
        ): Promise<void> => {
            await download(DOWNLOAD_URL, progress, token, internalActionServerLocation);
        }
    );
}

const getInternalActionServerDirLocation = async (): Promise<string> => {
    const robocorpHome: string = await getRobocorpHome();
    return path.join(robocorpHome, "action-server-vscode");
};

const getInternalActionServerLocation = async (tmpFlag: string = "") => {
    let binName: string = process.platform === "win32" ? `action-server${tmpFlag}.exe` : `action-server${tmpFlag}`;
    return path.join(await getInternalActionServerDirLocation(), binName);
};

export const getActionServerVersion = async (actionServerLocation: string): Promise<string | undefined> => {
    let result: ExecFileReturn;
    const maxTimes = 4;
    let lastError = undefined;
    for (let checkedTimes = 0; checkedTimes < maxTimes; checkedTimes++) {
        try {
            result = await execFilePromise(actionServerLocation, ["version"], {});
            // this is the version
            return result.stdout.trim();
        } catch (err) {
            lastError = err;
            // In Windows right after downloading the file it may not be executable,
            // so, retry a few times.
            await sleep(250);
        }
    }
    const msg = `There was an error running the action server at: ${actionServerLocation}. It may be unusable or you may not have permissions to run it.`;
    logError(msg, lastError, "ERR_VERIFY_ACTION_SERVER_VERSION");
    window.showErrorMessage(msg);
    throw lastError;
};

let verifiedActionServerVersions: Map<string, boolean> = new Map();

export const downloadLatestActionServer = async (): Promise<string | undefined> => {
    const tmpLocation = await getInternalActionServerLocation(`-${Date.now()}`);
    OUTPUT_CHANNEL.appendLine(`Downloading latest Action Server to ${tmpLocation}.`);
    await makeDirs(path.dirname(tmpLocation));
    await downloadActionServer(tmpLocation);
    const version = await getActionServerVersion(tmpLocation);
    OUTPUT_CHANNEL.appendLine("Checking version of latest Action Server.");
    const versionedLocation = await getInternalActionServerLocation(`-${version}`);
    const source = Uri.file(tmpLocation);
    const target = Uri.file(versionedLocation);
    OUTPUT_CHANNEL.appendLine(`Putting in final location (${target}).`);
    await workspace.fs.rename(source, target, { overwrite: true });
    setActionserverLocation(versionedLocation);
    return versionedLocation;
};

export const downloadOrGetActionServerLocation = async (): Promise<string | undefined> => {
    const location = await internalDownloadOrGetActionServerLocation();
    if (!location) {
        return location;
    }
    const verifiedAlready = verifiedActionServerVersions.get(location);
    if (!verifiedAlready) {
        verifiedActionServerVersions.set(location, true);
        const actionServerVersion = await getActionServerVersion(location);

        const expected = LATEST_ACTION_SERVER_VERSION;
        const compare = compareVersions(expected, actionServerVersion);
        if (compare > 0) {
            const DOWNLOAD = "Download new";
            const selection = await showSelectOneStrQuickPick(
                [DOWNLOAD, "Keep current"],
                "How would you like to proceed.",
                `Old version of Action Server detected (${actionServerVersion}). Expected '${expected}' or newer.`
            );
            if (selection === DOWNLOAD) {
                return await downloadLatestActionServer();
            }
        }
    }
    return location;
};

const internalDownloadOrGetActionServerLocation = async (): Promise<string | undefined> => {
    let actionServerLocationInSettings = getActionserverLocation();
    let message: string | undefined = undefined;
    if (!actionServerLocationInSettings) {
        message =
            "The action-server executable is not currently specified in the `robocorp.actionServerLocation` setting. How would you like to proceed?";
    } else if (!(await fileExists(actionServerLocationInSettings))) {
        message =
            "The action-server executable specified in the `robocorp.actionServerLocation` does not point to an existing file. How would you like to proceed?";
    } else {
        // Ok, found in settings.
        return actionServerLocationInSettings;
    }

    if (message) {
        const DOWNLOAD_TO_INTERNAL_LOCATION = "Download";
        const SPECIFY_LOCATION = "Specify Location";
        const option = await window.showInformationMessage(
            message,
            { "modal": true },
            DOWNLOAD_TO_INTERNAL_LOCATION,
            SPECIFY_LOCATION
        );
        if (option === DOWNLOAD_TO_INTERNAL_LOCATION) {
            return await downloadLatestActionServer();
        } else if (option === SPECIFY_LOCATION) {
            let uris: Uri[] | undefined = await window.showOpenDialog({
                "canSelectFolders": false,
                "canSelectFiles": true,
                "canSelectMany": false,
                "openLabel": `Select the action-server executable`,
            });
            if (uris && uris.length === 1) {
                const f = uris[0].fsPath;
                setActionserverLocation(f);
                return f;
            }
            return undefined;
        }
    }

    return undefined;
};

const isActionServerAlive = async (port) => {
    try {
        await fetchData(port, "/openapi.json", "GET");
        return true;
    } catch (err) {
        return false;
    }
};

function makeRequest(postData: string, options: http.RequestOptions): Promise<string> {
    return new Promise((resolve, reject) => {
        const req = http.request(options, (res) => {
            let responseData = "";

            res.setEncoding("utf8");
            res.on("data", (chunk) => {
                responseData += chunk;
            });

            res.on("end", () => {
                resolve(responseData);
            });
        });

        req.on("error", (error) => {
            reject(error);
        });

        req.write(postData);
        req.end();
    });
}

/**
 * @param path this is the path in the host (i.e.: /api-endpoint)
 */
async function fetchData(port: number, path: string, method: "POST" | "GET") {
    const postData = JSON.stringify({});

    const options: http.RequestOptions = {
        hostname: "localhost",
        port: port,
        path: path,
        method: method,
        headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(postData),
        },
    };

    return await makeRequest(postData, options);
}

const shutdownExistingActionServer = async (port) => {
    await fetchData(port, "/api/shutdown", "POST");
};

const port = 8082;

const ACTION_SERVER_TERMINAL_NAME = "Robocorp: Action Server";

const getActionServerTerminal = (): undefined | Terminal => {
    for (const terminal of window.terminals) {
        if (terminal.name === ACTION_SERVER_TERMINAL_NAME) {
            return terminal;
        }
    }
    return undefined;
};

export const startActionServer = async (directory: Uri) => {
    if (!directory) {
        // Need to list the action packages available to decide
        // which one to use for the action server.
        const selected = await listAndAskRobotSelection(
            "Please select the Action Package from which the Action Server should load actions.",
            "Unable to start Action Server because no Action Package was found in the workspace.",
            { showActionPackages: true, showTaskPackages: false }
        );
        if (!selected) {
            return;
        }
        directory = Uri.file(selected.directory);
    }

    let actionServerTerminal: Terminal = getActionServerTerminal();
    if (actionServerTerminal !== undefined) {
        if (await isActionServerAlive(port)) {
            const RESTART = "Restart action server";
            const option = await window.showWarningMessage(
                "The action server seems to be running already. How do you want to proceed?",
                RESTART,
                "Cancel"
            );
            if (option !== RESTART) {
                return;
            }
            await shutdownExistingActionServer(port);
            actionServerTerminal.dispose();
            actionServerTerminal = undefined;
        } else {
            OUTPUT_CHANNEL.appendLine("Action server not alive.");
            actionServerTerminal.dispose();
            actionServerTerminal = undefined;
        }
    }

    // We need to:
    // Get action server executable (download if not there)
    const location = await downloadOrGetActionServerLocation();
    if (!location) {
        return;
    }

    const env = createEnvWithRobocorpHome(await getRobocorpHome());
    env["RC_ADD_SHUTDOWN_API"] = "1";

    actionServerTerminal = window.createTerminal({
        name: "Robocorp: Action Server",
        env: env,
        cwd: directory,
    });

    actionServerTerminal.show();
    OUTPUT_CHANNEL.appendLine("Starting action-server (in terminal): " + location);

    actionServerTerminal.sendText(""); // Just add a new line in case something is there already.
    actionServerTerminal.sendText(`cd ${directory.fsPath}`);
    actionServerTerminal.sendText(`${location} start --port=${port}`);
};
