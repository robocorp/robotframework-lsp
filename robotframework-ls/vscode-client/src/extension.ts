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

function startLangServerIO(command: string, args: string[], documentSelector: string[]): LanguageClient {
	const serverOptions: ServerOptions = {
		command,
		args,
	};
	const clientOptions: LanguageClientOptions = {
		documentSelector: documentSelector,
		synchronize: {
			configurationSection: "robot"
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
			configurationSection: "robot"
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



class RobotDebugConfigurationProvider implements DebugConfigurationProvider {

	resolveDebugConfiguration(folder: WorkspaceFolder | undefined, debugConfiguration: DebugConfiguration, token?: CancellationToken): ProviderResult<DebugConfiguration> {
		// When we resolve a configuration we add the pythonpath and variables to the command line.
		let args: Array<string> = debugConfiguration.args;
		let config = workspace.getConfiguration("robot");
		let pythonpath: Array<string> = config.get<Array<string>>("pythonpath");
		let variables: object = config.get("variables");

		let newArgs = [];
		pythonpath.forEach(element => {
			newArgs.push('--pythonpath');
			newArgs.push(element);
		});

		for (let key in variables) {
			if (variables.hasOwnProperty(key)) {
				newArgs.push('--variable');
				newArgs.push(key + ':' + variables[key]);
			}
		}
		if (args) {
			args = args.concat(newArgs);
		} else {
			args = newArgs;
		}
		debugConfiguration.args = args;
		return debugConfiguration;
	};
}


function registerDebugger(languageServerExecutable: string) {
	function createDebugAdapterExecutable(env: { [key: string]: string }): DebugAdapterExecutable {
		let config = workspace.getConfiguration("robot");
		let dapPythonExecutable: string = config.get<string>("python.executable");

		if (!dapPythonExecutable) {
			// If the dapPythonExecutable is not specified, use the default language server executable.
			if (!languageServerExecutable) {
				window.showWarningMessage('Error getting language server python executable for creating a debug adapter.');
				return;
			}
			dapPythonExecutable = languageServerExecutable;
		}

		let targetFile: string = path.resolve(__dirname, '../../src/robotframework_debug_adapter/__main__.py');
		if (!fs.existsSync(targetFile)) {
			window.showWarningMessage('Error. Expected: ' + targetFile + " to exist.");
			return;
		}
		if (!fs.existsSync(dapPythonExecutable)) {
			window.showWarningMessage('Error. Expected: ' + dapPythonExecutable + " to exist.");
			return;
		}
		if (env) {
			return new DebugAdapterExecutable(dapPythonExecutable, ['-u', targetFile], { "env": env });

		} else {
			return new DebugAdapterExecutable(dapPythonExecutable, ['-u', targetFile]);
		}
	};


	debug.registerDebugAdapterDescriptorFactory('robotframework-lsp', {
		createDebugAdapterDescriptor: session => {
			let env = session.configuration.env;
			return createDebugAdapterExecutable(env);
		}
	});

	debug.registerDebugConfigurationProvider('robotframework-lsp', new RobotDebugConfigurationProvider());
}



interface ExecutableAndMessage {
	executable: string;
	message: string;
}


function getDefaultLanguageServerPythonExecutable(): ExecutableAndMessage {
	let config = workspace.getConfiguration("robot");
	let languageServerPython: string = config.get<string>("language-server.python");
	let executable: string = languageServerPython;

	if (!executable || (executable.indexOf('/') == -1 && executable.indexOf('\\') == -1)) {
		// Search python from the path.
		if (!executable) {
			if (process.platform == "win32") {
				executable = findExecutableInPath("python.exe");
			} else {
				executable = findExecutableInPath("python3");
				if (!fs.existsSync(executable)) {
					executable = findExecutableInPath("python");
				}
			}
		} else {
			executable = findExecutableInPath(executable);
		}
		if (!fs.existsSync(executable)) {
			return {
				executable: undefined,
				'message': 'Unable to start robotframework-lsp because: python could not be found on the PATH. Do you want to select a python executable to start robotframework-lsp?'
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
				'message': 'Unable to start robotframework-lsp because: ' + executable + ' does not exist. Do you want to select a new python executable to start robotframework-lsp?'
			};
		}
		return {
			executable: executable,
			'message': undefined
		};
	}
}



export async function activate(context: ExtensionContext) {
	try {
		// The first thing we need is the python executable.
		let executableAndMessage = getDefaultLanguageServerPythonExecutable();
		if (executableAndMessage.message) {
			let saveInUser: string = 'Yes (save in user settings)';
			let saveInWorkspace: string = 'Yes (save in workspace settings)';

			let selection = await window.showWarningMessage(executableAndMessage.message, ...[saveInUser, saveInWorkspace, 'No']);
			// robot.language-server.python
			if (selection == saveInUser || selection == saveInWorkspace) {
				let onfulfilled = await window.showOpenDialog({
					'canSelectMany': false,
					'openLabel': 'Select python exe'
				});
				if (!onfulfilled && onfulfilled.length > 0) {
					let configurationTarget: ConfigurationTarget = ConfigurationTarget.Workspace;
					if (selection == saveInUser) {
						configurationTarget = ConfigurationTarget.Global;
					}
					let config = workspace.getConfiguration("robot");
					config.update("language-server.python", onfulfilled[0].fsPath, configurationTarget);
					executableAndMessage = { 'executable': onfulfilled[0].fsPath, message: undefined };
				}
			} else {
				// There's not much we can do (besides start listening to changes to the related variables
				// on the finally block so that we start listening and ask for a reload if a related configuration changes).
				return;
			}
		}

		let config = workspace.getConfiguration("robot");
		let port: number = config.get<number>("language-server.tcp-port");
		let langServer: LanguageClient;
		if (port) {
			// For TCP server needs to be started seperately
			langServer = startLangServerTCP(port, ["robotframework"]);

		} else {
			let targetFile: string = path.resolve(__dirname, '../../src/robotframework_ls/__main__.py');
			if (!fs.existsSync(targetFile)) {
				window.showWarningMessage('Error. Expected: ' + targetFile + " to exist.");
				return;
			}

			let args: Array<string> = ["-u", targetFile];
			let config = workspace.getConfiguration("robot");
			let lsArgs = config.get<Array<string>>("language-server.args");
			if (lsArgs) {
				args = args.concat(lsArgs);
			}
			langServer = startLangServerIO(executableAndMessage.executable, args, ["robotframework"]);
		}
		let disposable: Disposable = langServer.start();
		registerDebugger(executableAndMessage.executable);
		context.subscriptions.push(disposable);

	} finally {
		workspace.onDidChangeConfiguration(event => {
			for (let s of ["robot.language-server.python", "robot.language-server.tcp-port", "robot.language-server.args"]) {
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


