"use strict";

import * as path from "path";
import * as fs from "fs";
import { Uri, window, workspace } from "vscode";
import { OUTPUT_CHANNEL } from "./channel";
import { join } from "path";

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

export async function isFile(filename: string): Promise<boolean> {
    try {
        const stat = await fs.promises.stat(filename);
        return stat.isFile();
    } catch (err) {
        return false;
    }
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

export async function readFromFile(targetFile: string) {
    if (!(await fileExists(targetFile))) {
        return undefined;
    }
    const contents = await fs.promises.readFile(targetFile);
    return contents.toString();
}

export async function writeToFile(
    targetFile: string,
    content: string,
    options?: fs.BaseEncodingOptions
): Promise<void> {
    return await fs.promises.writeFile(targetFile, content, options);
}

export async function makeDirs(targetDir: string) {
    await fs.promises.mkdir(targetDir, { recursive: true });
}

export async function findNextBasenameIn(folder: string, prefix: string) {
    const check = join(folder, prefix);
    if (!(await fileExists(check))) {
        return prefix; // Use as is directly
    }
    for (let i = 1; i < 9999; i++) {
        const basename = `${prefix}-${i}`;
        const check = join(folder, basename);
        if (!(await fileExists(check))) {
            return basename;
        }
    }
    throw new Error(`Unable to find valid name in ${folder} for prefix: ${prefix}.`);
}
