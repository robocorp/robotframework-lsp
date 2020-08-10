import * as fs from 'fs';
import { XHRResponse, configure as configureXHR, xhr } from './requestLight';
import { getExtensionRelativeFile } from './files';
import { workspace, window, ProgressLocation, CancellationToken, Progress } from 'vscode';
import { OUTPUT_CHANNEL } from './channel';
import { Timing, sleep } from './time';

async function downloadRcc(progress: Progress<{ message?: string; increment?: number }>, token: CancellationToken): Promise<string | undefined> {

    // Configure library with http settings.
    // i.e.: https://code.visualstudio.com/docs/setup/network
    let httpSettings = workspace.getConfiguration('http');
    configureXHR(httpSettings.get<string>('proxy'), httpSettings.get<boolean>('proxyStrictSSL'));
    let location = getExpectedRccLocation();
    let url: string;
    if (process.platform == 'win32') {
        if (process.arch === 'x64' || process.env.hasOwnProperty('PROCESSOR_ARCHITEW6432')) {
            // Check if node is a 64 bit process or if it's a 32 bit process running in a 64 bit processor.
            url = 'https://downloads.code.robocorp.com/rcc/windows64/rcc.exe';
        } else {
            // Do we even have a way to test a 32 bit build?
            url = 'https://downloads.code.robocorp.com/rcc/windows32/rcc.exe';

        }
    } else if (process.platform == 'darwin') {
        url = 'https://downloads.code.robocorp.com/rcc/macos64/rcc';

    } else {
        // Linux
        if (process.arch === 'x64') {
            url = 'https://downloads.code.robocorp.com/rcc/linux64/rcc';
        } else {
            url = 'https://downloads.code.robocorp.com/rcc/linux32/rcc';
        }
    }

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
