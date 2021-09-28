"use strict";

import { OUTPUT_CHANNEL } from "./channel";
import { execFile, ExecException, ExecFileOptions } from "child_process";
import { getExtensionRelativeFile } from "./files";

export interface ExecFileError {
    error: ExecException;
    stdout: string;
    stderr: string;
}

export interface ExecFileReturn {
    stdout: string;
    stderr: string;
}

async function _execFileAsPromise(command: string, args: string[], options: ExecFileOptions): Promise<ExecFileReturn> {
    return new Promise((resolve, reject) => {
        execFile(command, args, options, (error, stdout, stderr) => {
            if (error) {
                reject({ error: "error", "stdout": stdout, "stderr": stderr });
                return;
            }
            resolve({ "stdout": stdout, "stderr": stderr });
        });
    });
}

function getDefaultCwd(): string {
    return getExtensionRelativeFile("../../bin", false);
}

/**
 * @param options may be something as: { env: { ...process.env, ENV_VAR: 'test' } }
 */
export async function execFilePromise(
    command: string,
    args: string[],
    options: ExecFileOptions
): Promise<ExecFileReturn> {
    OUTPUT_CHANNEL.appendLine("Executing: " + command + "," + args);
    try {
        if (!options.cwd) {
            options.cwd = getDefaultCwd();
        }
        return await _execFileAsPromise(command, args, options);
    } catch (exc) {
        let errorInfo: ExecFileError = exc;
        let error: ExecException = errorInfo.error;

        OUTPUT_CHANNEL.appendLine("Error executing: " + command + "," + args);
        OUTPUT_CHANNEL.appendLine("Error code: " + error.code);
        OUTPUT_CHANNEL.appendLine("Error: " + error);
        if (error.name) {
            OUTPUT_CHANNEL.appendLine("Error name: " + error.name);
        }
        if (errorInfo.stderr) {
            OUTPUT_CHANNEL.appendLine("Stderr: " + errorInfo.stderr);
        }
        if (errorInfo.stdout) {
            OUTPUT_CHANNEL.appendLine("Stdout: " + errorInfo.stdout);
        }
        throw exc;
    }
}
