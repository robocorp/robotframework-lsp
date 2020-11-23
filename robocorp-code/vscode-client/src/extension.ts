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
import * as fs from 'fs';
import * as path from 'path';

import { workspace, Disposable, ExtensionContext, window, commands, WorkspaceFolder, ProgressLocation, Progress, DebugAdapterExecutable, debug, DebugConfiguration, DebugConfigurationProvider, CancellationToken, ProviderResult, extensions, ConfigurationTarget } from 'vscode';
import { LanguageClient, LanguageClientOptions, ServerOptions } from 'vscode-languageclient';
import * as views from './views';
import * as roboConfig from './robocorpSettings';
import * as roboCommands from './robocorpCommands';
import { OUTPUT_CHANNEL } from './channel';
import { getExtensionRelativeFile, verifyFileExists } from './files';
import { getRccLocation } from './rcc';
import { Timing } from './time';
import { execFilePromise, ExecFileReturn } from './subprocess';
import { createRobot, uploadRobot, cloudLogin, runRobotRCC, cloudLogout, setPythonInterpreterFromRobotYaml, askAndRunRobotRCC } from './activities';
import { sleep } from './time';
import { handleProgressMessage, ProgressReport } from './progress';
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE } from './robocorpViews';


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

interface InterpreterInfo {
    pythonExe: string;
    environ?: { [key: string]: string };
    additionalPythonpathEntries: string[];
}

interface ActionResult {
    success: boolean;
    message: string;
    result: any;
}


class RobocorpCodeDebugConfigurationProvider implements DebugConfigurationProvider {

    provideDebugConfigurations?(folder: WorkspaceFolder | undefined, token?: CancellationToken): DebugConfiguration[] {
        let configurations: DebugConfiguration[] = [];
        configurations.push({
            "type": "robocorp-code",
            "name": "Robocorp Code: Launch task from robot.yaml",
            "request": "launch",
            "robot": '^"\\${file}"',
            "task": "",
        });
        return configurations;
    };

    async resolveDebugConfigurationWithSubstitutedVariables(folder: WorkspaceFolder | undefined, debugConfiguration: DebugConfiguration, token?: CancellationToken): Promise<DebugConfiguration> {
        if (debugConfiguration.noDebug) {
            // Not running with debug: just use rcc to launch.
            return debugConfiguration;
        }
        // If it's a debug run, we need to get the input contents -- something as:
        // "type": "robocorp-code",
        // "name": "Robocorp Code: Launch task from current robot.yaml",
        // "request": "launch",
        // "robot": "c:/robot.yaml",
        // "task": "entrypoint",
        //
        // and convert it to the contents expected by robotframework-lsp:
        //
        // "type": "robotframework-lsp",
        // "name": "Robot: Current File",
        // "request": "launch",
        // "cwd": "${workspaceFolder}",
        // "target": "c:/task.robot",
        //
        // (making sure that we can actually do this and it's a robot launch for the task)

        if (!fs.existsSync(debugConfiguration.robot)) {
            window.showWarningMessage('Error. Expected: specified "robot": ' + debugConfiguration.robot + " to exist.");
            return;
        }

        // Note: this will also activate robotframework-lsp if it's still not activated.
        let interpreter: InterpreterInfo = undefined;
        try {
            interpreter = await commands.executeCommand('robot.resolveInterpreter', debugConfiguration.robot);
        } catch (error) {
            window.showWarningMessage('Error resolving interpreter info: ' + error);
            return;
        }

        if (!interpreter) {
            window.showErrorMessage("Unable to resolve robot.yaml based on: " + debugConfiguration.robot)
            return;
        }

        let actionResult: ActionResult = await commands.executeCommand(roboCommands.ROBOCORP_COMPUTE_ROBOT_LAUNCH_FROM_ROBOCORP_CODE_LAUNCH, {
            'name': debugConfiguration.name,
            'request': debugConfiguration.request,
            'robot': debugConfiguration.robot,
            'task': debugConfiguration.task,
            'additionalPythonpathEntries': interpreter.additionalPythonpathEntries,
            'env': interpreter.environ,
            'pythonExe': interpreter.pythonExe,
        });

        if (!actionResult.success) {
            window.showErrorMessage(actionResult.message)
            return;
        }
        let result = actionResult.result
        if (result && result.type && result.type == 'python') {
            let extension = extensions.getExtension('ms-python.python');
            if (extension) {
                if (!extension.isActive) {
                    // i.e.: Auto-activate python extension for the launch as the extension
                    // is only activated for debug on the resolution, whereas in this case
                    // the launch is already resolved.
                    await extension.activate();
                }
            }
        }

        return result;
    };
}



function registerDebugger(pythonExecutable: string) {
    async function createDebugAdapterExecutable(config: DebugConfiguration): Promise<DebugAdapterExecutable> {
        let env = config.env;
        let robotHome = roboConfig.getHome();
        if (robotHome && robotHome.length > 0) {
            if (env) {
                env['ROBOCORP_HOME'] = robotHome;
            } else {
                env = { 'ROBOCORP_HOME': robotHome };
            }
        }
        let targetMain: string = path.resolve(__dirname, '../../src/robocorp_code_debug_adapter/__main__.py');
        if (!fs.existsSync(targetMain)) {
            window.showWarningMessage('Error. Expected: ' + targetMain + " to exist.");
            return;
        }
        if (!fs.existsSync(pythonExecutable)) {
            window.showWarningMessage('Error. Expected: ' + pythonExecutable + " to exist.");
            return;
        }
        if (env) {
            return new DebugAdapterExecutable(pythonExecutable, ['-u', targetMain], { "env": env });

        } else {
            return new DebugAdapterExecutable(pythonExecutable, ['-u', targetMain]);
        }
    };


    debug.registerDebugAdapterDescriptorFactory('robocorp-code', {
        createDebugAdapterDescriptor: session => {
            const config: DebugConfiguration = session.configuration;
            return createDebugAdapterExecutable(config);
        }
    });

    debug.registerDebugConfigurationProvider('robocorp-code', new RobocorpCodeDebugConfigurationProvider());
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
        commands.registerCommand(roboCommands.ROBOCORP_CREATE_ROBOT, () => createRobot());
        commands.registerCommand(roboCommands.ROBOCORP_UPLOAD_ROBOT_TO_CLOUD, () => uploadRobot());
        commands.registerCommand(roboCommands.ROBOCORP_RUN_ROBOT_RCC, () => askAndRunRobotRCC(true));
        commands.registerCommand(roboCommands.ROBOCORP_DEBUG_ROBOT_RCC, () => askAndRunRobotRCC(false));
        commands.registerCommand(roboCommands.ROBOCORP_SET_PYTHON_INTERPRETER, () => setPythonInterpreterFromRobotYaml());
        commands.registerCommand(roboCommands.ROBOCORP_REFRESH_ROBOTS_VIEW, () => views.refreshTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE));
        commands.registerCommand(roboCommands.ROBOCORP_ROBOTS_VIEW_TASK_RUN, () => views.runSelectedRobot(true));
        commands.registerCommand(roboCommands.ROBOCORP_ROBOTS_VIEW_TASK_DEBUG, () => views.runSelectedRobot(false));
        async function cloudLoginShowConfirmation() {
            let loggedIn = await cloudLogin();
            if (loggedIn) {
                window.showInformationMessage("Successfully logged in Robocorp Cloud.")
            }
        }
        commands.registerCommand(roboCommands.ROBOCORP_CLOUD_LOGIN, () => cloudLoginShowConfirmation());
        commands.registerCommand(roboCommands.ROBOCORP_CLOUD_LOGOUT, () => cloudLogout());
        views.registerViews(context);
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

    let robotYaml = getExtensionRelativeFile('../../bin/create_env/robot.yaml');
    if (!robotYaml) {
        return;
    }

    async function createDefaultEnv(progress: Progress<{ message?: string; increment?: number }>): Promise<ExecFileReturn> | undefined {
        // Check that ROBOCORP_HOME is valid (i.e.: doesn't have any spaces in it).
        let robocorpHome: string = roboConfig.getHome();
        if (!robocorpHome || robocorpHome.length == 0) {
            robocorpHome = process.env['ROBOCORP_HOME'];
            if (!robocorpHome) {
                try {
                    let condaCheckResult: ExecFileReturn = await execFilePromise(rccLocation, ['env', 'variables', '-r', robotYaml, '--controller', 'RobocorpCode'], {});
                    let splitted: string[] = condaCheckResult.stdout.split('\n');
                    for (let index = 0; index < splitted.length; index++) {
                        const element = splitted[index];
                        if (element.startsWith('ROBOCORP_HOME=')) {
                            robocorpHome = element.substring('ROBOCORP_HOME='.length);
                            break;
                        }
                    }
                } catch (err) {
                    OUTPUT_CHANNEL.appendLine(err);
                }
            }
        }
        OUTPUT_CHANNEL.appendLine('ROBOCORP_HOME: ' + robocorpHome);

        while (!robocorpHome || robocorpHome.length == 0 || robocorpHome.indexOf(' ') != -1) {
            const SELECT_ROBOCORP_HOME = 'Set new ROBOCORP_HOME';
            const CANCEL = "Cancel";
            let result = await window.showInformationMessage(
                "The current ROBOCORP_HOME is invalid (paths with spaces are not supported).",
                SELECT_ROBOCORP_HOME,
                CANCEL
            );
            if (!result || result == CANCEL) {
                OUTPUT_CHANNEL.appendLine('Cancelled setting new ROBOCORP_HOME.');
                return undefined;
            }

            let uriResult = await window.showOpenDialog({
                'canSelectFolders': true,
                'canSelectFiles': false,
                'canSelectMany': false,
                'openLabel': 'Set as ROBOCORP_HOME'
            });
            if (!uriResult) {
                OUTPUT_CHANNEL.appendLine('Cancelled getting ROBOCORP_HOME path.');
                return undefined;
            }
            if (uriResult.length != 1) {
                OUTPUT_CHANNEL.appendLine('Expected 1 path to set as ROBOCORP_HOME. Found: ' + uriResult.length);
                return undefined;
            }
            robocorpHome = uriResult[0].fsPath;
            OUTPUT_CHANNEL.appendLine('Selected ROBOCORP_HOME: ' + robocorpHome);
            let config = workspace.getConfiguration('robocorp');
            await config.update('home', robocorpHome, ConfigurationTarget.Global);
        }

        // Make sure that conda is installed.
        const maxTries = 5;
        progress.report({ message: 'Get conda (may take a few minutes).' });
        let timing = new Timing();
        for (let index = 0; index < maxTries; index++) {
            try {
                let condaCheckResult: ExecFileReturn = await execFilePromise(
                    rccLocation, ['conda', 'check', '-i', '--controller', 'RobocorpCode'],
                    { env: { ...process.env, ROBOCORP_HOME: robocorpHome } }
                );
                if (condaCheckResult.stderr.indexOf('OK.') != -1) {
                    break;
                }
                // Note: checking if conda is there is the first thing and sometimes
                // it seems that right after downloading RCC, trying to run it right away doesn't work.
                // So, try to retry if it doesn't work out.
                OUTPUT_CHANNEL.appendLine('Expected OK. to be in the stderr. Found:\nStdout: ' + condaCheckResult.stdout + '\nStderr:' + condaCheckResult.stderr);

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
        let resultPromise: Promise<ExecFileReturn> = execFilePromise(
            rccLocation, ['task', 'run', '--robot', robotYaml, '--controller', 'RobocorpCode'],
            { env: { ...process.env, ROBOCORP_HOME: robocorpHome } }
        );
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

    let result: ExecFileReturn | undefined = await window.withProgress({
        location: ProgressLocation.Notification,
        title: "Robocorp",
        cancellable: false
    }, createDefaultEnv);

    function disabled(msg: string): undefined {
        msg = 'Robocorp Code extension disabled. Reason: ' + msg;
        OUTPUT_CHANNEL.appendLine(msg);
        window.showErrorMessage(msg);
        return undefined;
    }

    if (!result) {
        return disabled('Unable to get python to launch language server.');
    }
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
        return disabled('Python executable: ' + pythonExe + ' does not exist.');
    } catch (error) {
        return disabled('Unable to get python to launch language server.\nStderr: ' + result.stderr + '\nStdout (json contents): ' + result.stdout);
    }
}
