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

import { workspace, Disposable, ExtensionContext, window, commands, Uri, ConfigurationTarget, debug, DebugAdapterExecutable } from 'vscode';
import { LanguageClientOptions } from 'vscode-languageclient';
import { LanguageClient, ServerOptions } from 'vscode-languageclient/node';

function startLangServerIO(command: string, args: string[], documentSelector: string[]): LanguageClient {
	const serverOptions: ServerOptions = {
		command,
		args,
	};
	const clientOptions: LanguageClientOptions = {
		documentSelector: documentSelector,
		synchronize: {
			configurationSection: "example"
		}
	}
	// See: https://code.visualstudio.com/api/language-extensions/language-server-extension-guide
	return new LanguageClient(command, serverOptions, clientOptions);
}

function startLangServerTCP(addr: number, documentSelector: string[]): LanguageClient {
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

	const clientOptions: LanguageClientOptions = {
		documentSelector: documentSelector,
		synchronize: {
			configurationSection: "example"
		}
	}
	return new LanguageClient(`tcp lang server (port ${addr})`, serverOptions, clientOptions);
}

function findExecutableInPath(executable: string) {
	const IS_WINDOWS = process.platform == "win32";
	const sep = IS_WINDOWS ? ";" : ":";
	const PATH = process.env["PATH"];
	const split = PATH.split(sep);
	for (let i = 0; i < split.length; i++) {
		const s = path.join(split[i], executable);
		if (fs.existsSync(s)) {
			return s;
		}
	}
	return undefined;
}

function askPythonExe(context: ExtensionContext, askMessage: string) {
	let saveInUser: string = 'Yes (save in user settings)';
	let saveInWorkspace: string = 'Yes (save in workspace settings)';

	window.showWarningMessage(askMessage, ...[saveInUser, saveInWorkspace, 'No']).then((selection) => {
		// example.language-server.python
		if (selection == saveInUser || selection == saveInWorkspace) {
			window.showOpenDialog({
				'canSelectMany': false,
				'openLabel': 'Select python exe'
			}).then(onfulfilled => {
				if (onfulfilled && onfulfilled.length > 0) {
					let configurationTarget: ConfigurationTarget = ConfigurationTarget.Workspace;
					if (selection == saveInUser) {
						configurationTarget = ConfigurationTarget.Global;
					}
					let config = workspace.getConfiguration("example");
					ignoreNextConfigurationChange = true;
					config.update("language-server.python", onfulfilled[0].fsPath, configurationTarget);
					startLangServerIOWithPython(context, onfulfilled[0].fsPath);
				}
			});
		}
	});
}



function afterStartLangServer(pythonExecutable: string) {
    // Register additional things (for instance, debugger).
}

function startLangServerIOWithPython(context: ExtensionContext, pythonExecutable: string) {
	let targetFile: string = path.resolve(__dirname, '../../src/example_vscode/__main__.py');
	if (!fs.existsSync(targetFile)) {
		window.showWarningMessage('Error. Expected: ' + targetFile + " to exist.");
		return;
	}

	let args: Array<string> = ["-u", targetFile];
	let config = workspace.getConfiguration("example");
	let lsArgs = config.get<Array<string>>("language-server.args");
	if (lsArgs) {
		args = args.concat(lsArgs);
	}

	let langServer: LanguageClient = startLangServerIO(pythonExecutable, args, ["example_vscode"]);
	let disposable: Disposable = langServer.start();
	afterStartLangServer(pythonExecutable);
	context.subscriptions.push(disposable);

}


// i.e.: we can ignore changes when we know we'll be doing them prior to starting the language server.
let ignoreNextConfigurationChange: boolean = false;

function startListeningConfigurationChanges() {

	workspace.onDidChangeConfiguration(event => {
		if (ignoreNextConfigurationChange) {
			ignoreNextConfigurationChange = false;
			return;
		}
		for (let s of ["example.language-server.python", "example.language-server.tcp-port", "example.language-server.args"]) {
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

function getDefaultLanguageServerPythonExecutable() {
	let config = workspace.getConfiguration("example");
	let languageServerPython: string = config.get<string>("language-server.python");
	let executable: string = languageServerPython;

	if (!executable || (executable.indexOf('/') == -1 && executable.indexOf('\\') == -1)) {
		// Search python from the path.
		if (!executable || executable == "python") {
			if (process.platform == "win32") {
				executable = "python.exe";
			}
		}
		executable = findExecutableInPath(executable);
		if (!fs.existsSync(executable)) {
			return {
				executable: undefined,
				'message': 'Unable to start example_vscode because: python could not be found on the PATH. Do you want to select a python executable to start example_vscode?'
			};
		}
		return {
			executable: executable,
			'message': undefined
		};

	} else {
		if (!fs.existsSync(executable)) {
			return {
				executable: undefined,
				'message': 'Unable to start example_vscode because: ' + executable + ' does not exist. Do you want to select a new python executable to start example_vscode?'
			};
		}
		return {
			executable: executable,
			'message': undefined
		};
	}
}

export function activate(context: ExtensionContext) {
	let config = workspace.getConfiguration("example");


	try {
		let port: number = config.get<number>("language-server.tcp-port");
		if (port) {
			// For TCP server needs to be started seperately
			let langServer = startLangServerTCP(port, ["example_vscode"]);
			let disposable: Disposable = langServer.start();
			afterStartLangServer(undefined);
			context.subscriptions.push(disposable);

		} else {
			let executableAndMessage = getDefaultLanguageServerPythonExecutable();
			if (executableAndMessage.message) {
				askPythonExe(context, executableAndMessage.message);
				return;
			}

			startLangServerIOWithPython(context, executableAndMessage.executable);
		}
	} finally {
		startListeningConfigurationChanges();
	}

}

