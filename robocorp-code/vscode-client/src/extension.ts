/*
Original work Copyright (c) Microsoft Corporation (MIT)
See ThirdPartyNotices.txt in the project root for license information.
All modifications Copyright (c) Robocorp Technologies Inc.
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License")
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http: // www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

'use strict';

import * as net from 'net';

import { workspace, Disposable, ExtensionContext, window, commands, WorkspaceFolder, ProgressLocation, Progress } from 'vscode';
import { LanguageClient, LanguageClientOptions, ServerOptions } from 'vscode-languageclient';
import * as roboConfig from './robocorpSettings';
import * as roboCommands from './robocorpCommands';
import { OUTPUT_CHANNEL } from './channel';
import { getExtensionRelativeFile, verifyFileExists } from './files';
import { getRccLocation } from './rcc';
import { Timing } from './time';
import { execFilePromise, ExecFileReturn } from './subprocess';
import { createActivity, uploadActivity } from './activities';
import { sleep } from './time';
import { handleProgressMessage, ProgressReport } from './progress';


const clientOptions: LanguageClientOptions = {
    documentSelector: [],
    synchronize: {
        configurationSection: "robocorp"
    },
    outputChannel: OUTPUT_CHANNEL,
}


function startLangServerIO(command: string, args: string[]): LanguageClient {
    const serverOptions: ServerOptions = {
        command,
        args,
    };
    // See: https://code.visualstudio.com/api/language-extensions/language-server-extension-guide
    return new LanguageClient(command, serverOptions, clientOptions);
}

function startLangServerTCP(addr: number): LanguageClient {
    const serverOptions: ServerOptions = function () {
        return new Promise((resolve, reject) => {
            var client = new net.Socket();
            client.connect(addr, "127.0.0.1", function () {
                resolve({
                    reader: client,
                    writer: client
                });
            });
        });
    }


    return new LanguageClient(`tcp lang server (port ${addr})`, serverOptions, clientOptions);
}


function registerDebugger(languageServerExecutable: string) {
    // TODO: Actually provide support to launch an activity.
}

let langServer: LanguageClient;


export async function activate(context: ExtensionContext) {
    try {
        let timing = new Timing();
        // The first thing we need is the python executable.
        OUTPUT_CHANNEL.appendLine("Activating Robocorp Code extension.");
        let executable = await getLanguageServerPython();
        if (!executable) {
            OUTPUT_CHANNEL.appendLine("Unable to activate Robocorp Code extension (unable to get python executable).");
            return;
        }
        OUTPUT_CHANNEL.appendLine("Using python executable: " + executable);

        let port: number = roboConfig.getLanguageServerTcpPort();
        if (port) {
            // For TCP server needs to be started seperately
            langServer = startLangServerTCP(port);

        } else {
            let targetFile: string = getExtensionRelativeFile('../../src/robocorp_code/__main__.py');
            if (!targetFile) {
                return;
            }

            let args: Array<string> = ["-u", targetFile];
            let lsArgs = roboConfig.getLanguageServerArgs();
            if (lsArgs) {
                args = args.concat(lsArgs);
            }
            langServer = startLangServerIO(executable, args);
        }

        let disposable: Disposable = langServer.start();
        commands.registerCommand(roboCommands.ROBOCORP_GET_LANGUAGE_SERVER_PYTHON, () => getLanguageServerPython());
        commands.registerCommand(roboCommands.ROBOCORP_CREATE_ACTIVITY, () => createActivity());
        commands.registerCommand(roboCommands.ROBOCORP_UPLOAD_ACTIVITY_TO_CLOUD, () => uploadActivity());
        registerDebugger(executable);
        context.subscriptions.push(disposable);

        // i.e.: if we return before it's ready, the language server commands
        // may not be available.
        OUTPUT_CHANNEL.appendLine("Waiting for Robocorp Code (python) language server to finish activating...");
        await langServer.onReady();
        OUTPUT_CHANNEL.appendLine("Robocorp Code extension ready. Took: " + timing.getTotalElapsedAsStr());
        
        langServer.onNotification("$/customProgress", (args: ProgressReport) => {
            // OUTPUT_CHANNEL.appendLine(args.id + ' - ' + args.kind + ' - ' + args.title + ' - ' + args.message + ' - ' + args.increment);
            handleProgressMessage(args)
        });

    } finally {
        workspace.onDidChangeConfiguration(event => {
            for (let s of [roboConfig.ROBOCORP_LANGUAGE_SERVER_ARGS, roboConfig.ROBOCORP_LANGUAGE_SERVER_PYTHON, roboConfig.ROBOCORP_LANGUAGE_SERVER_TCP_PORT]) {
                if (event.affectsConfiguration(s)) {
                    window.showWarningMessage('Please use the "Reload Window" action for changes in ' + s + ' to take effect.', ...["Reload Window"]).then((selection) => {
                        if (selection === "Reload Window") {
                            commands.executeCommand("workbench.action.reloadWindow");
                        }
                    });
                    return;
                }
            }
        });
    }
}

export function deactivate(): Thenable<void> | undefined {
    if (!langServer) {
        return undefined;
    }
    return langServer.stop();
}


let cachedPythonExe: string;


async function getLanguageServerPython(): Promise<string> {
    if (cachedPythonExe) {
        return cachedPythonExe;
    }
    let pythonExe = await getLanguageServerPythonUncached();
    if (!pythonExe) {
        return undefined; // Unable to get it.
    }
    // Ok, we got it (cache that info).
    cachedPythonExe = pythonExe;
    return cachedPythonExe;
}


async function getLanguageServerPythonUncached(): Promise<string> {
    let rccLocation = await getRccLocation();
    if (!rccLocation) {
        return;
    }

    let packageYaml = getExtensionRelativeFile('../../bin/create_env/package.yaml');
    if (!packageYaml) {
        return;
    }

    async function createDefaultEnv(progress: Progress<{ message?: string; increment?: number }>): Promise<ExecFileReturn> {
        // Make sure that conda is installed.
        const maxTries = 5;
        progress.report({ message: 'Get conda (may take a few minutes).' });
        let timing = new Timing();
        for (let index = 0; index < maxTries; index++) {
            try {
                let condaCheckResult: ExecFileReturn = await execFilePromise(rccLocation, ['conda', 'check', '-i']);
                if (condaCheckResult.stdout.indexOf('OK.') != -1) {
                    break;
                }
                // Note: checking if conda is there is the first thing and sometimes
                // it seems that right after downloading RCC, trying to run it right away doesn't work.
                // So, try to retry if it doesn't work out.
                OUTPUT_CHANNEL.appendLine('Expected OK. to be in the stdout. Found:\nStdout: ' + condaCheckResult.stdout + '\nStderr:' + condaCheckResult.stderr);

                // We couldn't find OK. Let's retry.
                if (index == maxTries - 1) {
                    throw Error("Unable to install conda with RCC. Extension won't be usable (see Debug Console output for details).");
                } else {
                    OUTPUT_CHANNEL.appendLine('Will retry shortly...');
                }
            } catch (err) {
                // Some error happened. Let's retry.
                if (index == maxTries - 1) {
                    throw Error("Unable to install conda with RCC. Extension won't be usable (see Debug Console output for details).");
                } else {
                    OUTPUT_CHANNEL.appendLine('Will retry shortly...');
                }
            }
            await sleep(250);
        }

        OUTPUT_CHANNEL.appendLine('Took ' + timing.getTotalElapsedAsStr() + ' to get conda.')

        progress.report({ message: 'Update env (may take a few minutes).' });
        // Get information on a base package with our basic dependencies (this can take a while...).
        let resultPromise: Promise<ExecFileReturn> = execFilePromise(rccLocation, ['activity', 'run', '-p', packageYaml]);
        timing = new Timing();

        let finishedCondaRun = false;
        let onFinish = function () {
            finishedCondaRun = true;
        }
        resultPromise.then(onFinish, onFinish);

        // Busy async loop so that we can show the elapsed time.
        while (true) {
            await sleep(93); // Strange sleep so it's not always a .0 when showing ;)
            if (finishedCondaRun) {
                break;
            }
            if (timing.elapsedFromLastMeasurement(5000)) {
                progress.report({ message: 'Update env (may take a few minutes). ' + timing.getTotalElapsedAsStr() + ' elapsed.' });
            }
        }
        let result = await resultPromise;
        OUTPUT_CHANNEL.appendLine('Took ' + timing.getTotalElapsedAsStr() + ' to update conda env.')
        return result;
    }

    let result: ExecFileReturn = await window.withProgress({
        location: ProgressLocation.Notification,
        title: "Robocorp",
        cancellable: false
    }, createDefaultEnv);

    try {
        let jsonContents = result.stderr;
        let start: number = jsonContents.indexOf('JSON START>>')
        let end: number = jsonContents.indexOf('<<JSON END')
        if (start == -1 || end == -1) {
            throw Error("Unable to find JSON START>> or <<JSON END");
        }
        start += 'JSON START>>'.length;
        jsonContents = jsonContents.substr(start, end - start);
        OUTPUT_CHANNEL.appendLine('Parsing json contents: ' + jsonContents);
        let contents: object = JSON.parse(jsonContents);
        let pythonExe = contents['python_executable'];
        if (verifyFileExists(pythonExe)) {
            return pythonExe;
        }
    } catch (error) {
        OUTPUT_CHANNEL.appendLine('Unable to get python to launch language server.\nStderr: ' + result.stderr + '\nStdout (json contents): ' + result.stdout);
        return;
    }
    return undefined;
}
