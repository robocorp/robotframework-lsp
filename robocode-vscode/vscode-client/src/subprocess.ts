'use strict';

import * as util from 'util';
import { sleep } from './time';
import { OUTPUT_CHANNEL } from './channel';

interface ExecFileReturn {
    stdout: string;
    stderr: string;
};

const execFile = util.promisify(require('child_process').execFile);

export async function execFilePromise(command: string, args: string[]): Promise<ExecFileReturn> {
    const maxTries = 5;
    for (let index = 0; index < maxTries; index++) {
        OUTPUT_CHANNEL.appendLine('Executing: ' + command + ',' + args);
        try {
            return await execFile(command, args);
        } catch (error) {
            OUTPUT_CHANNEL.appendLine('Error executing: ' + command + ',' + args);
            OUTPUT_CHANNEL.appendLine('Error code: ' + error.code);
            OUTPUT_CHANNEL.appendLine('Error errno: ' + error.errno);
            OUTPUT_CHANNEL.appendLine('Error: ' + error);
            if(error.name){
                OUTPUT_CHANNEL.appendLine('Error name: ' + error.name);
            }
            if(error.stderr){
                OUTPUT_CHANNEL.appendLine('Stderr: ' + error.stderr);
            }
            if(error.stdout){
                OUTPUT_CHANNEL.appendLine('Stdout: ' + error.stdout);
            }
            if (error.code == 'EBUSY') {
                // After downloading a resource (such as rcc), on Windows, sometimes
                // it can take a while for the file to be really available to be used
                // (because ntfs is async or some antivirus is running) -- in this case,
                // we auto-retry a few times before giving up.
                if (index == maxTries - 1) {
                    OUTPUT_CHANNEL.appendLine('No more retries left (throwing error).');
                    throw error;
                }
                OUTPUT_CHANNEL.appendLine('Will retry shortly...');
                await sleep(200);
            } else {
                throw error;
            }
        }
    }
}
