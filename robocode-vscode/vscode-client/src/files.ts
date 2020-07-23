'use strict';

import * as path from 'path';
import * as fs from 'fs';
import { window } from 'vscode';
import { OUTPUT_CHANNEL } from './channel';

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

export function verifyFileExists(targetFile: string): boolean {
    if (!fs.existsSync(targetFile)) {
        let msg = 'Error. Expected: ' + targetFile + " to exist.";
        window.showWarningMessage(msg);
        OUTPUT_CHANNEL.appendLine(msg);
        return false;
    }
    return true;
}