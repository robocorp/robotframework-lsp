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
import * as path from 'path';
import * as fs from 'fs';

import { workspace, Disposable, ExtensionContext, window, commands, Uri, ConfigurationTarget, debug, DebugAdapterExecutable, ProviderResult, DebugConfiguration, WorkspaceFolder, CancellationToken, DebugConfigurationProvider } from 'vscode';
import { LanguageClient, LanguageClientOptions, SettingMonitor, ServerOptions, ErrorAction, ErrorHandler, CloseAction, TransportKind } from 'vscode-languageclient';
import * as roboConfig from './robocodeSettings';
import * as roboCommands from './robocodeCommands';
import * as childProcess from 'child_process';

const OUTPUT_CHANNEL_NAME = "Robocode";
const OUTPUT_CHANNEL = window.createOutputChannel(OUTPUT_CHANNEL_NAME);

const clientOptions: LanguageClientOptions = {
    documentSelector: [],
    synchronize: {
        configurationSection: "robocode"
    },
    outputChannel: OUTPUT_CHANNEL,
}

function verifyFileExists(targetFile: string): boolean {
    if (!fs.existsSync(targetFile)) {
        let msg = 'Error. Expected: ' + targetFile + " to exist.";
        window.showWarningMessage(msg);
        OUTPUT_CHANNEL.appendLine(msg);
        return false;
    }
    return true;
}

function getExtensionRelativeFile(relativeLocation: string): string | undefined {
    let targetFile: string = path.resolve(__dirname, relativeLocation);
    if (!verifyFileExists(targetFile)) {
        return undefined;
    }
    return targetFile;
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
        // The first thing we need is the python executable.
        OUTPUT_CHANNEL.appendLine("Activating Robocode extension.");
        let executable = await getLanguageServerPython();
        if (!executable) {
            OUTPUT_CHANNEL.appendLine("Unable to activate Robocode extension (unable to get python executable).");
            return;
        }
        OUTPUT_CHANNEL.appendLine("Using python executable: " + executable);

        let port: number = roboConfig.getLanguageServerTcpPort();
        if (port) {
            // For TCP server needs to be started seperately
            langServer = startLangServerTCP(port);

        } else {
            let targetFile: string = getExtensionRelativeFile('../../src/robocode_vscode/__main__.py');
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
        commands.registerCommand(roboCommands.ROBOCODE_GET_LANGUAGE_SERVER_PYTHON, () => getLanguageServerPython());
        registerDebugger(executable);
        context.subscriptions.push(disposable);

        // i.e.: if we return before it's ready, the language server commands
        // may not be available.
        OUTPUT_CHANNEL.appendLine("Waiting for Robocode (python) language server to finish activating...");
        await langServer.onReady();
        OUTPUT_CHANNEL.appendLine("Robocode extension ready.");


    } finally {
        workspace.onDidChangeConfiguration(event => {
            for (let s of [roboConfig.ROBOCODE_LANGUAGE_SERVER_ARGS, roboConfig.ROBOCODE_LANGUAGE_SERVER_PYTHON, roboConfig.ROBOCODE_LANGUAGE_SERVER_TCP_PORT]) {
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

// We can't really ship rcc per-platform right now (so, we need to either
// download it or ship it along).
// See: https://github.com/microsoft/vscode/issues/6929
// See: https://github.com/microsoft/vscode/issues/23251
// In particular, if we download things, we should use:
// https://www.npmjs.com/package/request-light according to:
// https://github.com/microsoft/vscode/issues/6929#issuecomment-222153748

function getRccLocation(): string | undefined {
    // TODO: Support other platforms
    return getExtensionRelativeFile('../../bin/rcc.exe');
}


interface ExecFileReturn {
    stdout: string;
    stderr: string;
};

function execFilePromise(command: string, args: string[]): Promise<ExecFileReturn> {
    return new Promise<ExecFileReturn>(function (resolve, reject) {
        OUTPUT_CHANNEL.appendLine('Executing: ' + command + ',' + args);
        childProcess.execFile(command, args, (error, stdout, stderr) => {
            if (error) {
                OUTPUT_CHANNEL.appendLine('Error executing: ' + command + ',' + args);
                OUTPUT_CHANNEL.appendLine('Error: ' + error);
                OUTPUT_CHANNEL.appendLine('Stderr: ' + stderr);
                OUTPUT_CHANNEL.appendLine('Stdout: ' + stdout);
                reject(error);
                return;
            }

            resolve({ 'stdout': stdout.trim(), 'stderr': stderr.trim() });
        });
    });
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
    let rccLocation = getRccLocation();
    if (!rccLocation) {
        return;
    }

    let packageYaml = getExtensionRelativeFile('../../bin/create_env/package.yaml');
    if (!packageYaml) {
        return;
    }

    // Make sure that conda is installed.
    await execFilePromise(rccLocation, ['conda', 'check', '-i']);

    // Get information on a base package with our basic dependencies (this can take a while...).
    let result = await execFilePromise(rccLocation, ['activity', 'run', '-p', packageYaml]);

    let contents: object;
    try {
        contents = JSON.parse(result.stderr);
        let pythonExe = contents['python_executable'];
        if (verifyFileExists) {
            return pythonExe;
        }
    } catch (error) {
        OUTPUT_CHANNEL.appendLine('Unable to get python to launch language server. Error parsing json: ' + result.stderr);
        return;
    }
    return undefined;
}
