/* --------------------------------------------------------------------------------------------
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See License.txt in the project root for license information.
 * ------------------------------------------------------------------------------------------ */
'use strict';

import * as net from 'net';
import * as path from 'path';
import * as fs from 'fs';

import { workspace, Disposable, ExtensionContext, window, commands } from 'vscode';
import { LanguageClient, LanguageClientOptions, SettingMonitor, ServerOptions, ErrorAction, ErrorHandler, CloseAction, TransportKind } from 'vscode-languageclient';
import { print } from 'util';
import { exec } from 'child_process';

function startLangServer(command: string, args: string[], documentSelector: string[]): LanguageClient {
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

export function activate(context: ExtensionContext) {
	let config = workspace.getConfiguration("robot");

	workspace.onDidChangeConfiguration(event => {
		for (let s of ["robot.language-server.python", "robot.language-server.tcp-port", "robot.language-server.args"]) {
			if (event.affectsConfiguration(s)) {
				window.showWarningMessage('Please use "Reload Window" action for changes in ' + s + ' to take effect.', ...["Reload Window"]).then((selection) => {
					if (selection === "Reload Window") {
						commands.executeCommand("workbench.action.reloadWindow");
					}
				});
				return;
			}
		}
	});

	let port: number = config.get<number>("language-server.tcp-port");
	if (port) {
		// For TCP server needs to be started seperately
		context.subscriptions.push(startLangServerTCP(port, ["robotframework"]).start());

	} else {
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
				window.showWarningMessage('Could not find python executable on PATH. Please specify in option: robot.language-server.python');
				return;
			}
		} else {
			if (!fs.existsSync(executable)) {
				window.showWarningMessage('Option: robot.language-server.python points to wrong file: ' + executable);
				return;
			}
		}

		let targetFile: string = path.resolve(__dirname, '../../src/robotframework_ls/__main__.py');
		if (!fs.existsSync(targetFile)) {
			window.showWarningMessage('Error. Expected: ' + targetFile + " to exist.");
			return;
		}

		let args: Array<string> = ["-u", targetFile];
		let lsArgs = config.get<Array<string>>("language-server.args");
		if (lsArgs) {
			args = args.concat(lsArgs);
		}

		let langServer: LanguageClient = startLangServer(executable, args, ["robotframework"]);
		let disposable: Disposable = langServer.start();
		context.subscriptions.push(disposable);
	}

}

