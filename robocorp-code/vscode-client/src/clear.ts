import { OUTPUT_CHANNEL, logError } from "./channel";
import { createEnvWithRobocorpHome, feedbackRobocorpCodeError } from "./rcc";
import { execFilePromise, ExecFileReturn } from "./subprocess";
import * as path from "path";
import * as fs from "fs";
import * as vscode from "vscode";

export interface IJsonSpaceInfo {
    blueprint: string;
    controller: string;
    id: string;
    meta: string;
    path: string;
    plan: string;
    space: string;
    spec: string;
}

export async function clearRCCEnvironments(
    rccLocation: string,
    robocorpHome: string,
    envsToCollect: IJsonSpaceInfo[],
    progress: vscode.Progress<{ message?: string; increment?: number }>
) {
    const env = createEnvWithRobocorpHome(robocorpHome);

    let i: number = 0;
    for (const envToCollect of envsToCollect) {
        i += 1;
        try {
            const envId = envToCollect["id"];
            progress.report({
                "message": `Deleting env: ${envId} (${i} of ${envsToCollect.length})`,
            });
            let execFileReturn: ExecFileReturn = await execFilePromise(
                rccLocation,
                ["holotree", "delete", envId, "--controller", "RobocorpCode"],
                { "env": env },
                { "showOutputInteractively": true }
            );
        } catch (error) {
            let msg = "Error collecting RCC environment: " + envToCollect.id + " at: " + envToCollect.path;
            logError(msg, error, "RCC_CLEAR_ENV");
        }
    }
}

async function removeCaches(dirPath: string, level: number, removeDirsArray: string[]) {
    let dirContents = await fs.promises.readdir(dirPath, { withFileTypes: true });

    for await (const dirEnt of dirContents) {
        var entryPath = path.join(dirPath, dirEnt.name);

        if (dirEnt.isDirectory()) {
            await removeCaches(entryPath, level + 1, removeDirsArray);
            removeDirsArray.push(entryPath);
        } else {
            try {
                await fs.promises.unlink(entryPath);
                OUTPUT_CHANNEL.appendLine(`Removed: ${entryPath}.`);
            } catch (err) {
                OUTPUT_CHANNEL.appendLine(`Unable to remove: ${entryPath}. ${err}`);
            }
        }
    }

    if (level === 0) {
        // Remove the (empty) directories only after all iterations finished.
        for (const entryPath of removeDirsArray) {
            try {
                await fs.promises.rmdir(entryPath);
                OUTPUT_CHANNEL.appendLine(`Removed dir: ${entryPath}.`);
            } catch (err) {
                OUTPUT_CHANNEL.appendLine(`Unable to remove dir: ${entryPath}. ${err}`);
            }
        }
    }
}

export async function clearRobocorpCodeCaches(robocorpHome: string) {
    let robocorpCodePath = path.join(robocorpHome, ".robocorp_code");
    removeCaches(robocorpCodePath, 0, []);
}

export async function computeEnvsToCollect(
    rccLocation: string,
    robocorpHome: string
): Promise<IJsonSpaceInfo[] | undefined> {
    let args = ["holotree", "list", "--json", "--controller", "RobocorpCode"];

    let execFileReturn: ExecFileReturn = await execFilePromise(
        rccLocation,
        args,
        { "env": createEnvWithRobocorpHome(robocorpHome) },
        { "showOutputInteractively": true }
    );
    if (!execFileReturn.stdout) {
        feedbackRobocorpCodeError("RCC_NO_RCC_ENV_STDOUT_ON_ENVS_TO_COLLECT");
        OUTPUT_CHANNEL.appendLine("Error: Unable to collect environment from RCC.");
        return undefined;
    }
    let nameToEnvInfo: { [key: string]: IJsonSpaceInfo } | undefined = undefined;
    try {
        nameToEnvInfo = JSON.parse(execFileReturn.stdout);
    } catch (error) {
        logError(
            "Error parsing env from RCC: " + execFileReturn.stdout,
            error,
            "RCC_WRONG_RCC_ENV_STDOUT_ON_ENVS_TO_COLLECT"
        );
        return undefined;
    }
    if (!nameToEnvInfo) {
        OUTPUT_CHANNEL.appendLine("Error: Unable to collect env array.");
        return undefined;
    }

    let found: IJsonSpaceInfo[] = [];

    for (const key in nameToEnvInfo) {
        if (Object.prototype.hasOwnProperty.call(nameToEnvInfo, key)) {
            const element = nameToEnvInfo[key];
            let spaceName = element["space"];
            if (spaceName && spaceName.startsWith("vscode")) {
                found.push(element);
            }
        }
    }
    return found;
}
