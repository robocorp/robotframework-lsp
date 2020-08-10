'use strict';

import { sleep } from './time';
import { OUTPUT_CHANNEL } from './channel';
import { execFile, ExecException } from 'child_process';

interface ExecFileError {
    error: ExecException;
    stdout: string;
    stderr: string;
};

interface ExecFileReturn {
    stdout: string;
    stderr: string;
};

async function _execFileAsPromise(command: string, args: string[]): Promise<ExecFileReturn> {
    return new Promise((resolve, reject) => {
        execFile(command, args, (error, stdout, stderr) => {
            if (error) {
                reject({ error: 'error', 'stdout': stdout, 'stderr': stderr });
                return;
            }
            resolve({ 'stdout': stdout, 'stderr': stderr });
        });
    });
}

export async function execFilePromise(command: string, args: string[]): Promise<ExecFileReturn> {
    OUTPUT_CHANNEL.appendLine('Executing: ' + command + ',' + args);
    try {
        return await _execFileAsPromise(command, args);
    } catch (exc) {
        let error_info: ExecFileError = exc;
        let error: ExecException = error_info.error;

        OUTPUT_CHANNEL.appendLine('Error executing: ' + command + ',' + args);
        OUTPUT_CHANNEL.appendLine('Error code: ' + error.code);
        OUTPUT_CHANNEL.appendLine('Error: ' + error);
        if (error.name) {
            OUTPUT_CHANNEL.appendLine('Error name: ' + error.name);
        }
        if (error_info.stderr) {
            OUTPUT_CHANNEL.appendLine('Stderr: ' + error_info.stderr);
        }
        if (error_info.stdout) {
            OUTPUT_CHANNEL.appendLine('Stdout: ' + error_info.stdout);
        }
        throw exc;
    }
}
