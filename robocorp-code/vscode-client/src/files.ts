"use strict";

import * as path from "path";
import * as fs from "fs";
import { Uri, window, workspace } from "vscode";
import { OUTPUT_CHANNEL } from "./channel";

/**
 * @param mustExist if true, if the returned file does NOT exist, returns undefined.
 */
export function getExtensionRelativeFile(relativeLocation: string, mustExist: boolean = true): string | undefined {
    let targetFile: string = path.resolve(__dirname, relativeLocation);
    if (mustExist) {
        if (!verifyFileExists(targetFile)) {
            return undefined;
        }
    }
    return targetFile;
}

export function verifyFileExists(targetFile: string, warnUser: boolean = true): boolean {
    if (!fs.existsSync(targetFile)) {
        let msg = "Error. Expected: " + targetFile + " to exist.";
        if (warnUser) window.showWarningMessage(msg);
        OUTPUT_CHANNEL.appendLine(msg);
        return false;
    }
    return true;
}

export async function fileExists(filename: string) {
    try {
        await fs.promises.stat(filename);
        return true;
    } catch (err) {
        return false;
    }
}

export async function uriExists(uri: Uri) {
    try {
        await workspace.fs.stat(uri);
        return true;
    } catch (err) {
        return false;
    }
}
