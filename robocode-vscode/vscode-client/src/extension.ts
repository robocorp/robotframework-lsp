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

const OUTPUT_CHANNEL_NAME = "Robocode";
const OUTPUT_CHANNEL = window.createOutputChannel(OUTPUT_CHANNEL_NAME);

const clientOptions: LanguageClientOptions = {
    documentSelector: [],
    synchronize: {
        configurationSection: "robocode"
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
    // TODO: Actually launch an activity.
}

let langServer: LanguageClient;

export async function activate(context: ExtensionContext) {
    try {
        // The first thing we need is the python executable.
        OUTPUT_CHANNEL.appendLine("Activating Robocode extension.");
        let executable = await getLanguageServerPython();
        if(!executable){
            OUTPUT_CHANNEL.appendLine("Unable to activate Robocode extension (unable to get python executable).");
            return;
        }
        OUTPUT_CHANNEL.appendLine("Using python executable: " + executable);

        let port: number = roboConfig.getLanguageServerTcpPort();
        if (port) {
            // For TCP server needs to be started seperately
            langServer = startLangServerTCP(port);

        } else {
            let targetFile: string = path.resolve(__dirname, '../../src/robocode_vscode/__main__.py');
            if (!fs.existsSync(targetFile)) {
                window.showWarningMessage('Error. Expected: ' + targetFile + " to exist.");
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

async function getLanguageServerPython() {
    return "C:/bin/Python37-32/python.exe";
}
