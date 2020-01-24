/* --------------------------------------------------------------------------------------------
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See License.txt in the project root for license information.
 * ------------------------------------------------------------------------------------------ */
'use strict';

import * as net from 'net';
import * as path from 'path';
import * as fs from 'fs';

import { workspace, Disposable, ExtensionContext, window } from 'vscode';
import { LanguageClient, LanguageClientOptions, SettingMonitor, ServerOptions, ErrorAction, ErrorHandler, CloseAction, TransportKind } from 'vscode-languageclient';
import { print } from 'util';

function startLangServer(command: string, args: string[], documentSelector: string[]): Disposable {
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
	return new LanguageClient(command, serverOptions, clientOptions).start();
}

function startLangServerTCP(addr: number, documentSelector: string[]): Disposable {
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
	return new LanguageClient(`tcp lang server (port ${addr})`, serverOptions, clientOptions).start();
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
	let executable: string = config.get<string>("python.executable");
	if (!executable) {
		// Search python from the path.
		if (process.platform == "win32") {
			executable = "python.exe";
		} else {
			executable = "python";
		}
		executable = findExecutableInPath(executable);
		if (!fs.existsSync(executable)) {
			window.showWarningMessage('Could not find python executable on PATH. Please specify in option: robot.python.executable');
			return;
		}
	} else {
		if (!fs.existsSync(executable)) {
			window.showWarningMessage('Option: robot.python.executable points to wrong file: ' + executable);
			return;
		}
	}
	
	let targetFile: string = path.resolve(__dirname, '../../robotframework_ls/__main__.py');
	if (!fs.existsSync(targetFile)) {
		window.showWarningMessage('Error. Expected: ' + targetFile + " to exist.");
		return;
	}

	let args: Array<string> = ["-u", targetFile];
	let lsArgs = config.get<Array<string>>("language-server.args");
	if(lsArgs) {
		args = args.concat(lsArgs);
	}


	context.subscriptions.push(startLangServer(executable, args, ["robot"]));
	// For TCP server needs to be started seperately
	// context.subscriptions.push(startLangServerTCP(2087, ["robot"]));
}

