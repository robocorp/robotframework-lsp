"use strict";

import { OUTPUT_CHANNEL } from "./channel";
import { execFile, ExecException, ExecFileOptions, ChildProcess } from "child_process";
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

async function _execFileAsPromise(
    command: string,
    args: string[],
    options: ExecFileOptions,
    configChildProcess?: (childProcess: ChildProcess) => void
): Promise<ExecFileReturn> {
    return new Promise((resolve, reject) => {
        let childProcess: ChildProcess = execFile(command, args, options, (error, stdout, stderr) => {
            if (error) {
                reject({ error: "error", "stdout": stdout, "stderr": stderr });
                return;
            }
            resolve({ "stdout": stdout, "stderr": stderr });
        });
        if (configChildProcess) {
            configChildProcess(childProcess);
        }
    });
}

function getDefaultCwd(): string {
    return getExtensionRelativeFile("../../bin", false);
}

interface ExecConfigOptions {
    // Default is showing command line (hideCommandLine = false).
    hideCommandLine?: boolean;

    // Callback called right after subprocess is created.
    configChildProcess?: (childProcess: ChildProcess) => void;

    // Default is showing output only on failures (showOutputInteractively = false).
    // If set, configChildProcess must be undefined.
    showOutputInteractively?: boolean;
}

/**
 * @param options may be something as: { env: { ...process.env, ENV_VAR: 'test' } }
 */
export async function execFilePromise(
    command: string,
    args: string[],
    options: ExecFileOptions,
    execConfigOptions?: ExecConfigOptions
): Promise<ExecFileReturn> {
    let hideCommandLine: boolean = false;
    let configChildProcess: (childProcess: ChildProcess) => void = undefined;
    let showOutputInteractively: boolean = false;

    if (execConfigOptions !== undefined) {
        hideCommandLine = execConfigOptions.hideCommandLine;
        configChildProcess = execConfigOptions.configChildProcess;
        showOutputInteractively = execConfigOptions.showOutputInteractively;

        if (showOutputInteractively) {
            if (configChildProcess !== undefined) {
                throw new Error("Error: if showOutputInteractively == true, configChildProcess must be undefined.");
            }
            configChildProcess = function (childProcess: ChildProcess) {
                childProcess.stderr.on("data", function (data: any) {
                    OUTPUT_CHANNEL.append(data);
                });
                childProcess.stdout.on("data", function (data: any) {
                    OUTPUT_CHANNEL.append(data);
                });
            };
        }
    }

    if (!hideCommandLine) {
        OUTPUT_CHANNEL.appendLine("Executing: " + command + " " + args.join(" "));
    }
    try {
        if (!options.cwd) {
            options.cwd = getDefaultCwd();
        }
        return await _execFileAsPromise(command, args, options, configChildProcess);
    } catch (exc) {
        let errorInfo: ExecFileError = exc;
        let error: ExecException = errorInfo.error;

        OUTPUT_CHANNEL.appendLine("Error executing: " + command + " " + args.join(" "));
        OUTPUT_CHANNEL.appendLine("Error code: " + error.code);
        OUTPUT_CHANNEL.appendLine("Error: " + error);
        if (error.name) {
            OUTPUT_CHANNEL.appendLine("Error name: " + error.name);
        }
        if (!showOutputInteractively) {
            // Only print stderr/stdout if output was not being shown interactively.
            if (errorInfo.stderr) {
                OUTPUT_CHANNEL.appendLine("Stderr: " + errorInfo.stderr);
            }
            if (errorInfo.stdout) {
                OUTPUT_CHANNEL.appendLine("Stdout: " + errorInfo.stdout);
            }
        }
        throw exc;
    }
}
