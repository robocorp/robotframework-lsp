import * as fs from 'fs';
import { XHRResponse, configure as configureXHR, xhr } from './requestLight';
import { getExtensionRelativeFile } from './files';
import { workspace } from 'vscode';
import { OUTPUT_CHANNEL } from './channel';
import { sleep, Timing } from './time';

// We can't really ship rcc per-platform right now (so, we need to either
// download it or ship it along).
// See: https://github.com/microsoft/vscode/issues/6929
// See: https://github.com/microsoft/vscode/issues/23251
// In particular, if we download things, we should use:
// https://www.npmjs.com/package/request-light according to:
// https://github.com/microsoft/vscode/issues/6929#issuecomment-222153748

export async function getRccLocation(): Promise<string | undefined> {
    let location: string;
    if (process.platform == 'win32') {
        location = getExtensionRelativeFile('../../bin/rcc.exe', false);
    } else {
        location = getExtensionRelativeFile('../../bin/rcc', false);
    }
    if (!fs.existsSync(location)) {
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

        // Configure library with http settings.
        // i.e.: https://code.visualstudio.com/docs/setup/network
        let httpSettings = workspace.getConfiguration('http');
        configureXHR(httpSettings.get<string>('proxy'), httpSettings.get<boolean>('proxyStrictSSL'));

        // Downloads can go wrong (so, retry a few times before giving up).
        const maxTries = 3;
        let timing: Timing = new Timing();

        function onProgress(currLen: number, totalLen: number) {
            if (timing.elapsedFromLastMeasurement(300)) {
                let progress = currLen / totalLen * 100;
                OUTPUT_CHANNEL.appendLine('Downloaded: ' + currLen + " of " + totalLen + " (" + progress.toFixed(1) + '%)');
            }
        }

        OUTPUT_CHANNEL.appendLine('Downloading rcc from: ' + url);
        for (let index = 0; index < maxTries; index++) {
            try {
                let response: XHRResponse = await xhr({
                    'url': url,
                    'onProgress': onProgress,
                });
                if (response.status == 200) {
                    // Ok, we've been able to get it.
                    OUTPUT_CHANNEL.appendLine('Finished downloading in: ' + timing.getTotalElapsedAsStr());
                    OUTPUT_CHANNEL.appendLine('Writing to: ' + location);
                    let s = fs.createWriteStream(location, { 'encoding': 'binary', 'mode': 0o744 });
                    try {
                        response.responseData.forEach(element => {
                            s.write(element);
                        });
                    } finally {
                        s.close();
                    }

                    return location;
                } else {
                    throw Error('Unable to download from ' + url + '. Response status: ' + response.status + 'Response message: ' + response.responseText);
                }
            } catch (error) {
                OUTPUT_CHANNEL.appendLine('Error downloading (' + index + ' of ' + maxTries + '). Error: ' + error);
                if (index == maxTries - 1) {
                    return undefined;
                }
            }
        }
    }
    return location;

}
