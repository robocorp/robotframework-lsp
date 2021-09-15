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

import {
    workspace,
    Disposable,
    ExtensionContext,
    window,
    commands,
    WorkspaceFolder,
    ProgressLocation,
    Progress,
    DebugAdapterExecutable,
    debug,
    DebugConfiguration,
    DebugConfigurationProvider,
    CancellationToken,
    ProviderResult,
    extensions,
    ConfigurationTarget,
    env,
    Uri,
} from 'vscode';
import { LanguageClientOptions, State } from 'vscode-languageclient';
import { LanguageClient, ServerOptions } from 'vscode-languageclient/node';
import * as inspector from './inspector';
import { copySelectedToClipboard, removeLocator } from './locators';
import * as views from './views';
import * as roboConfig from './robocorpSettings';
import * as roboCommands from './robocorpCommands';
import { logError, OUTPUT_CHANNEL } from './channel';
import { getExtensionRelativeFile, verifyFileExists } from './files';
import {
    collectBaseEnv,
    getRccLocation,
    RCCDiagnostics,
    runConfigDiagnostics,
    STATUS_FAIL,
    STATUS_FATAL,
    STATUS_OK,
    STATUS_WARNING,
    submitIssue,
    submitIssueUI,
} from './rcc';
import { Timing } from './time';
import { execFilePromise, ExecFileReturn } from './subprocess';
import {
    createRobot,
    uploadRobot,
    cloudLogin,
    runRobotRCC,
    cloudLogout,
    setPythonInterpreterFromRobotYaml,
    askAndRunRobotRCC,
    rccConfigurationDiagnostics,
} from './activities';
import { sleep } from './time';
import { handleProgressMessage, ProgressReport } from './progress';
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE, TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE } from './robocorpViews';
import { askAndCreateRccTerminal } from './rccTerminal';
import {
    deleteResourceInRobotContentTree,
    newFileInRobotContentTree,
    newFolderInRobotContentTree,
    renameResourceInRobotContentTree,
} from './viewsRobotContent';
import { LocatorEntry } from './viewsCommon';


const clientOptions: LanguageClientOptions = {
    documentSelector: [
        { language: 'json', pattern: '**/locators.json' },
        { language: 'yaml', pattern: '**/conda.yaml' },
        { language: 'yaml', pattern: '**/robot.yaml' }
    ],
    synchronize: {
        configurationSection: "robocorp"
    },
    outputChannel: OUTPUT_CHANNEL,
}


function startLangServerIO(command: string, args: string[], environ?: { [key: string]: string }): LanguageClient {
    const serverOptions: ServerOptions = {
        command,
        args,
    };
    if (!environ) {
        environ = process.env;
    }
    let src: string = path.resolve(__dirname, '../../src');
    serverOptions.options = { env: { ...environ, PYTHONPATH: src }, cwd: path.dirname(command) };

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
            logError('Error resolving interpreter info.', error);
            window.showWarningMessage('Error resolving interpreter info: ' + error.message);
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

async function verifyRobotFrameworkInstalled() {
    if (!roboConfig.getVerifylsp()) {
        return;
    }
    const ROBOT_EXTENSION_ID = 'robocorp.robotframework-lsp';
    let found = true;
    try {
        let extension = extensions.getExtension(ROBOT_EXTENSION_ID);
        if (!extension) {
            found = false;
        }
    } catch (error) {
        found = false;
    }
    if (!found) {
        // It seems it's not installed, install?
        let install = 'Install';
        let dontAsk = "Don't ask again";
        let chosen = await window.showInformationMessage(
            "It seems that the Robot Framework Language Server extension is not installed to work with .robot Files.",
            install,
            dontAsk
        );
        if (chosen == install) {
            commands.executeCommand('workbench.extensions.search', ROBOT_EXTENSION_ID);
        } else if (chosen == dontAsk) {
            roboConfig.setVerifylsp(false);
        }
    }
}


let langServer: LanguageClient;


export async function activate(context: ExtensionContext) {
    try {
        let timing = new Timing();
        // The first thing we need is the python executable.
        OUTPUT_CHANNEL.appendLine("Activating Robocorp Code extension.");


        const extension = extensions.getExtension("robocorp.robotframework-lsp");
        if (extension) {
            // If the Robot Framework Language server is present, make sure it is compatible with this
            // version.
            try {
                const version: string = extension.packageJSON.version;
                const splitted = version.split('.');
                const major = parseInt(splitted[0]);
                const minor = parseInt(splitted[1]);
                if (major == 0 && minor <= 20) {
                    const msg = 'Unable to initialize the Robocorp Code extension because the Robot Framework Language Server version (' +
                        version +
                        ') is not compatible with this version of Robocorp Code. Robot Framework Language Server 0.21.0 or newer is required. Please update to proceed. ';
                    OUTPUT_CHANNEL.appendLine(msg);
                    window.showErrorMessage(msg);
                    return;
                }
            } catch (err) {
                logError('Error verifying Robot Framework Language Server version.', err);
            }
        }



        // Note: register the submit issue actions early on so that we can later actually
        // report startup errors.
        let logPath: string = context.logPath;
        commands.registerCommand(roboCommands.ROBOCORP_SUBMIT_ISSUE, () => { submitIssueUI(logPath) });

        // i.e.: allow other extensions to also use our submit issue api.
        commands.registerCommand(roboCommands.ROBOCORP_SUBMIT_ISSUE_INTERNAL, (
            dialogMessage: string,
            email: string,
            errorName: string,
            errorCode: string,
            errorMessage: string,
        ) => submitIssue(
            logPath, // gotten from plugin context
            dialogMessage,
            email,
            errorName,
            errorCode,
            errorMessage)
        );

        let executableAndEnv = await getLanguageServerPythonInfo();
        if (!executableAndEnv) {
            OUTPUT_CHANNEL.appendLine("Unable to activate Robocorp Code extension (unable to get python executable).");
            return;
        }
        OUTPUT_CHANNEL.appendLine("Using python executable: " + executableAndEnv.pythonExe);
        let startLsTiming = new Timing();

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
            langServer = startLangServerIO(executableAndEnv.pythonExe, args, executableAndEnv.environ);
        }

        let stopListeningOnDidChangeState = langServer.onDidChangeState((event) => {
            if (event.newState == State.Running) {
                // i.e.: We need to register the customProgress as soon as it's running (we can't wait for onReady)
                // because at that point if there are open documents, lots of things may've happened already, in
                // which case the progress won't be shown on some cases where it should be shown.
                context.subscriptions.push(langServer.onNotification("$/customProgress", (args: ProgressReport) => {
                    // OUTPUT_CHANNEL.appendLine(args.id + ' - ' + args.kind + ' - ' + args.title + ' - ' + args.message + ' - ' + args.increment);
                    handleProgressMessage(args)
                }));
                context.subscriptions.push(langServer.onNotification("$/linkedAccountChanged", () => {
                    views.refreshCloudTreeView();
                }));
                stopListeningOnDidChangeState.dispose();
            }
        });
        let disposable: Disposable = langServer.start();
        commands.registerCommand(roboCommands.ROBOCORP_GET_LANGUAGE_SERVER_PYTHON, () => getLanguageServerPython());
        commands.registerCommand(roboCommands.ROBOCORP_GET_LANGUAGE_SERVER_PYTHON_INFO, () => getLanguageServerPythonInfo());
        commands.registerCommand(roboCommands.ROBOCORP_CREATE_ROBOT, () => createRobot());
        commands.registerCommand(roboCommands.ROBOCORP_UPLOAD_ROBOT_TO_CLOUD, () => uploadRobot());
        commands.registerCommand(roboCommands.ROBOCORP_CONFIGURATION_DIAGNOSTICS, () => rccConfigurationDiagnostics());
        commands.registerCommand(roboCommands.ROBOCORP_RUN_ROBOT_RCC, () => askAndRunRobotRCC(true));
        commands.registerCommand(roboCommands.ROBOCORP_DEBUG_ROBOT_RCC, () => askAndRunRobotRCC(false));
        commands.registerCommand(roboCommands.ROBOCORP_SET_PYTHON_INTERPRETER, () => setPythonInterpreterFromRobotYaml());
        commands.registerCommand(roboCommands.ROBOCORP_REFRESH_ROBOTS_VIEW, () => views.refreshTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE));
        commands.registerCommand(roboCommands.ROBOCORP_REFRESH_CLOUD_VIEW, () => views.refreshCloudTreeView());
        commands.registerCommand(roboCommands.ROBOCORP_ROBOTS_VIEW_TASK_RUN, () => views.runSelectedRobot(true));
        commands.registerCommand(roboCommands.ROBOCORP_ROBOTS_VIEW_TASK_DEBUG, () => views.runSelectedRobot(false));
        commands.registerCommand(roboCommands.ROBOCORP_EDIT_ROBOCORP_INSPECTOR_LOCATOR, (locator?: LocatorEntry) => inspector.openRobocorpInspector(undefined, locator));
        commands.registerCommand(roboCommands.ROBOCORP_NEW_ROBOCORP_INSPECTOR_BROWSER, () => inspector.openRobocorpInspector("browser"));
        commands.registerCommand(roboCommands.ROBOCORP_NEW_ROBOCORP_INSPECTOR_IMAGE, () => inspector.openRobocorpInspector("image"));
        commands.registerCommand(roboCommands.ROBOCORP_COPY_LOCATOR_TO_CLIPBOARD_INTERNAL, (locator?: LocatorEntry) => copySelectedToClipboard(locator));
        commands.registerCommand(roboCommands.ROBOCORP_REMOVE_LOCATOR_FROM_JSON, (locator?: LocatorEntry) => removeLocator(locator));
        commands.registerCommand(roboCommands.ROBOCORP_OPEN_ROBOT_TREE_SELECTION, () => views.openRobotTreeSelection());
        commands.registerCommand(roboCommands.ROBOCORP_CLOUD_UPLOAD_ROBOT_TREE_SELECTION, () => views.cloudUploadRobotTreeSelection());
        commands.registerCommand(roboCommands.ROBOCORP_CREATE_RCC_TERMINAL_TREE_SELECTION, () => views.createRccTerminalTreeSelection());
        commands.registerCommand(roboCommands.ROBOCORP_RCC_TERMINAL_NEW, () => askAndCreateRccTerminal());
        commands.registerCommand(roboCommands.ROBOCORP_REFRESH_ROBOT_CONTENT_VIEW, () => views.refreshTreeView(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE));
        commands.registerCommand(roboCommands.ROBOCORP_NEW_FILE_IN_ROBOT_CONTENT_VIEW, newFileInRobotContentTree);
        commands.registerCommand(roboCommands.ROBOCORP_NEW_FOLDER_IN_ROBOT_CONTENT_VIEW, newFolderInRobotContentTree);
        commands.registerCommand(roboCommands.ROBOCORP_DELETE_RESOURCE_IN_ROBOT_CONTENT_VIEW, deleteResourceInRobotContentTree);
        commands.registerCommand(roboCommands.ROBOCORP_RENAME_RESOURCE_IN_ROBOT_CONTENT_VIEW, renameResourceInRobotContentTree);
        async function cloudLoginShowConfirmationAndRefresh() {
            let loggedIn = await cloudLogin();
            if (loggedIn) {
                window.showInformationMessage("Successfully logged in Robocorp Cloud.")
            }
            views.refreshCloudTreeView();
        }
        async function cloudLogoutAndRefresh() {
            await cloudLogout();
            views.refreshCloudTreeView();
        }
        commands.registerCommand(roboCommands.ROBOCORP_CLOUD_LOGIN, () => cloudLoginShowConfirmationAndRefresh());
        commands.registerCommand(roboCommands.ROBOCORP_CLOUD_LOGOUT, () => cloudLogoutAndRefresh());
        views.registerViews(context);
        registerDebugger(executableAndEnv.pythonExe);
        context.subscriptions.push(disposable);


        // i.e.: if we return before it's ready, the language server commands
        // may not be available.
        OUTPUT_CHANNEL.appendLine("Waiting for Robocorp Code (python) language server to finish activating...");
        await langServer.onReady();
        OUTPUT_CHANNEL.appendLine("Took: " + startLsTiming.getTotalElapsedAsStr() + ' to initialize Robocorp Code Language Server.');
        OUTPUT_CHANNEL.appendLine("Robocorp Code extension ready. Took: " + timing.getTotalElapsedAsStr());

        verifyRobotFrameworkInstalled();

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


let _cachedPythonInfo: InterpreterInfo;


async function getLanguageServerPython(): Promise<string | undefined> {
    let info = await getLanguageServerPythonInfo();
    if (!info) {
        return undefined;
    }
    return info.pythonExe;
}


export async function getLanguageServerPythonInfo(): Promise<InterpreterInfo | undefined> {
    if (_cachedPythonInfo) {
        return _cachedPythonInfo;
    }
    let cachedPythonInfo = await getLanguageServerPythonInfoUncached();
    if (!cachedPythonInfo) {
        return undefined; // Unable to get it.
    }
    // Ok, we got it (cache that info).
    _cachedPythonInfo = cachedPythonInfo;
    return _cachedPythonInfo;
}

async function enableWindowsLongPathSupport(rccLocation: string) {
    try {
        try {
            // Expected failure if not admin.
            await execFilePromise(
                rccLocation, ['configure', 'longpaths', '--enable'],
                { env: { ...process.env } }
            );
            await sleep(100);
        } catch (error) {
            // Expected error (it means we need an elevated shell to run the command).
            try {
                // Now, at this point we resolve the links to have a canonical location, because
                // we'll execute with a different user (i.e.: admin), we first resolve substs
                // which may not be available for that user (i.e.: a subst can be applied to one
                // account and not to the other) because path.resolve and fs.realPathSync don't
                // seem to resolve substed drives, we do it manually here.

                if (rccLocation.charAt(1) == ':') { // Check that we're actually have a drive there.
                    try {
                        let resolved: string = fs.readlinkSync(rccLocation.charAt(0) + ':');
                        rccLocation = path.join(resolved, rccLocation.slice(2));
                    } catch (error) {
                        // ignore (it's not a link)
                    }
                }

                rccLocation = path.resolve(rccLocation);
                rccLocation = fs.realpathSync(rccLocation);
            } catch (error) {
                OUTPUT_CHANNEL.appendLine('Error (handled) resolving rcc canonical location: ' + error);
            }
            rccLocation = rccLocation.split('\\').join('/'); // escape for the shell execute
            let result: ExecFileReturn = await execFilePromise(
                'C:/Windows/System32/mshta.exe', // i.e.: Windows scripting
                [
                    "javascript: var shell = new ActiveXObject('shell.application');" + // create a shell
                    "shell.ShellExecute('" + rccLocation + "', 'configure longpaths --enable', '', 'runas', 1);close();" // runas will run in elevated mode
                ],
                { env: { ...process.env } }
            );
            // Wait a second for the command to be executed as admin before proceeding.
            await sleep(1000);
        }
    } catch (error) {
        // Ignore here...
    }
}

async function isLongPathSupportEnabledOnWindows(rccLocation: string): Promise<boolean> {
    let enabled: boolean = true;
    try {
        let configureLongpathsOutput: ExecFileReturn = await execFilePromise(
            rccLocation, ['configure', 'longpaths'],
            { env: { ...process.env } },
        );
        if (configureLongpathsOutput.stdout.indexOf('OK.') != -1 || configureLongpathsOutput.stderr.indexOf('OK.') != -1) {
            enabled = true;
        } else {
            enabled = false;
        }
    } catch (error) {
        enabled = false;
    }
    if (enabled) {
        OUTPUT_CHANNEL.appendLine('Windows long paths support enabled');
    } else {
        OUTPUT_CHANNEL.appendLine(
            'Windows long paths support NOT enabled.');
    }
    return enabled;
}

async function verifyLongPathSupportOnWindows(rccLocation: string): Promise<boolean> {
    if (process.platform == 'win32') {
        while (true) {
            let enabled: boolean = await isLongPathSupportEnabledOnWindows(rccLocation);

            if (!enabled) {
                const YES = 'Yes (requires elevated shell)';
                const MANUALLY = 'Open manual instructions';

                let result = await window.showErrorMessage(
                    "Windows long paths support (required by Robocorp Code) is not enabled. Would you like to have Robocorp Code enable it now?",
                    { 'modal': true },
                    YES,
                    MANUALLY,
                    // Auto-cancel in modal
                );
                if (result == YES) {
                    // Enable it.
                    await enableWindowsLongPathSupport(rccLocation);
                    let enabled = await isLongPathSupportEnabledOnWindows(rccLocation);
                    if (enabled) {
                        return true;
                    } else {
                        let result = await window.showErrorMessage(
                            "It was not possible to automatically enable windows long path support. " +
                            "Please follow the instructions from https://robocorp.com/docs/troubleshooting/windows-long-path (press Ok to open in browser).",
                            { 'modal': true },
                            'Ok',
                            // Auto-cancel in modal
                        );
                        if (result == 'Ok') {
                            await env.openExternal(Uri.parse('https://robocorp.com/docs/troubleshooting/windows-long-path'));
                        }
                    }
                } else if (result == MANUALLY) {
                    await env.openExternal(Uri.parse('https://robocorp.com/docs/troubleshooting/windows-long-path'));

                } else {
                    // Cancel
                    OUTPUT_CHANNEL.appendLine('Extension will not be activated because Windows long paths support not enabled.');
                    return false;
                }

                result = await window.showInformationMessage(
                    "Press Ok after Long Path support is manually enabled.",
                    { 'modal': true },
                    'Ok',
                    // Auto-cancel in modal
                );
                if (!result) {
                    OUTPUT_CHANNEL.appendLine('Extension will not be activated because Windows long paths support not enabled.');
                    return false;
                }

            } else {
                return true;
            }
        }
    }
    return true;
}

async function getLanguageServerPythonInfoUncached(): Promise<InterpreterInfo | undefined> {
    let rccLocation = await getRccLocation();
    if (!rccLocation) {
        OUTPUT_CHANNEL.appendLine('Unable to get rcc executable location.');
        return;
    }

    let robotYaml = getExtensionRelativeFile('../../bin/create_env/robot.yaml');
    if (!robotYaml) {
        OUTPUT_CHANNEL.appendLine('Unable to find: ../../bin/create_env/robot.yaml in extension.');
        return;
    }

    let robotConda: string;
    switch (process.platform) {
        case "darwin":
            robotConda = getExtensionRelativeFile('../../bin/create_env/conda_vscode_darwin_amd64.yaml');
            break;
        case "linux":
            robotConda = getExtensionRelativeFile('../../bin/create_env/conda_vscode_linux_amd64.yaml');
            break;
        case "win32":
            robotConda = getExtensionRelativeFile('../../bin/create_env/conda_vscode_windows_amd64.yaml');
            break;
        default:
            robotConda = getExtensionRelativeFile('../../bin/create_env/conda.yaml');
            break;
    }

    if (!robotConda) {
        OUTPUT_CHANNEL.appendLine('Unable to find: ../../bin/create_env/conda.yaml in extension.');
        return;
    }

    let getEnvInfoPy = getExtensionRelativeFile('../../bin/create_env/get_env_info.py');
    if (!getEnvInfoPy) {
        OUTPUT_CHANNEL.appendLine('Unable to find: ../../bin/create_env/get_env_info.py in extension.');
        return;
    }

    /**
     * @returns the result of running `get_env_info.py`.
     */
    async function createDefaultEnv(progress: Progress<{ message?: string; increment?: number }>): Promise<ExecFileReturn> | undefined {
        // Check that the user has long names enabled on windows.
        if (!await verifyLongPathSupportOnWindows(rccLocation)) {
            return undefined;
        }
        // Check that ROBOCORP_HOME is valid (i.e.: doesn't have any spaces in it).
        let robocorpHome: string = roboConfig.getHome();
        if (!robocorpHome || robocorpHome.length == 0) {
            robocorpHome = process.env['ROBOCORP_HOME'];
            if (!robocorpHome) {
                // Default from RCC (maybe it should provide an API to get it before creating an env?)
                if (process.platform == 'win32') {
                    robocorpHome = path.join(process.env.LOCALAPPDATA, 'robocorp');
                } else {
                    robocorpHome = path.join(process.env.HOME, '.robocorp');
                }
            }
        }
        OUTPUT_CHANNEL.appendLine('ROBOCORP_HOME: ' + robocorpHome);

        let rccDiagnostics: RCCDiagnostics | undefined = await runConfigDiagnostics(rccLocation, robocorpHome);
        if (!rccDiagnostics) {
            let msg = 'There was an error getting RCC diagnostics. Robocorp Code will not be started!';
            OUTPUT_CHANNEL.appendLine(msg);
            window.showErrorMessage(msg);
            return undefined;
        }

        while (!rccDiagnostics.isRobocorpHomeOk()) {
            const SELECT_ROBOCORP_HOME = 'Set new ROBOCORP_HOME';
            const CANCEL = "Cancel";
            let result = await window.showInformationMessage(
                "The current ROBOCORP_HOME is invalid (paths with spaces/non ascii chars are not supported).",
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
            rccDiagnostics = await runConfigDiagnostics(rccLocation, robocorpHome);
            if (!rccDiagnostics) {
                let msg = 'There was an error getting RCC diagnostics. Robocorp Code will not be started!';
                OUTPUT_CHANNEL.appendLine(msg);
                window.showErrorMessage(msg);
                return undefined;
            }
            if (rccDiagnostics.isRobocorpHomeOk()) {
                OUTPUT_CHANNEL.appendLine('Selected ROBOCORP_HOME: ' + robocorpHome);
                let config = workspace.getConfiguration('robocorp');
                await config.update('home', robocorpHome, ConfigurationTarget.Global);
            }
        }

        function createOpenUrl(failedCheck) {
            return (value) => {
                if (value == 'Open troubleshoot URL') {
                    env.openExternal(Uri.parse(failedCheck.url));
                }
            };
        }
        let canProceed: boolean = true;
        for (const failedCheck of rccDiagnostics.failedChecks) {
            if (failedCheck.status == STATUS_FATAL) {
                canProceed = false;
            }
            let func = window.showErrorMessage;
            if (failedCheck.status == STATUS_WARNING) {
                func = window.showWarningMessage;
            }
            if (failedCheck.url) {
                func(failedCheck.message, 'Open troubleshoot URL').then(createOpenUrl(failedCheck));
            } else {
                func(failedCheck.message)
            }
        }
        if (!canProceed) {
            return undefined;
        }

        progress.report({ message: 'Update env (may take a few minutes).' });
        // Get information on a base package with our basic dependencies (this can take a while...).
        let rccEnvPromise = collectBaseEnv(robotConda, robocorpHome);
        let timing = new Timing();

        let finishedCondaRun = false;
        let onFinish = function () {
            finishedCondaRun = true;
        }
        rccEnvPromise.then(onFinish, onFinish);

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
        let envResult = await rccEnvPromise;
        OUTPUT_CHANNEL.appendLine('Took: ' + timing.getTotalElapsedAsStr() + ' to update conda env.');

        if (!envResult) {
            OUTPUT_CHANNEL.appendLine('Error creating conda env.');
            return undefined;
        }
        // Ok, we now have the holotree space created and just collected the environment variables. Let's now do
        // a raw python run with that information to collect information from python.

        let pythonExe = envResult.env['PYTHON_EXE'];
        if (!pythonExe) {
            OUTPUT_CHANNEL.appendLine('Error: PYTHON_EXE not available in the holotree environment.');
            return undefined;
        }

        let pythonTiming = new Timing();
        let resultPromise: Promise<ExecFileReturn> = execFilePromise(
            pythonExe, [getEnvInfoPy],
            { env: envResult.env }
        );

        let finishedPythonRun = false;
        let onFinishPython = function () {
            finishedPythonRun = true;
        }
        resultPromise.then(onFinishPython, onFinishPython);

        // Busy async loop so that we can show the elapsed time.
        while (true) {
            await sleep(93); // Strange sleep so it's not always a .0 when showing ;)
            if (finishedPythonRun) {
                break;
            }
            if (timing.elapsedFromLastMeasurement(5000)) {
                progress.report({ message: 'Collecting env info. ' + timing.getTotalElapsedAsStr() + ' elapsed.' });
            }
        }
        let ret = await resultPromise;
        OUTPUT_CHANNEL.appendLine("Took: " + pythonTiming.getTotalElapsedAsStr() + " to collect python info.");
        return ret;
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
        let contents: object = JSON.parse(jsonContents);
        let pythonExe = contents['python_executable'];
        OUTPUT_CHANNEL.appendLine('Python executable: ' + pythonExe);
        OUTPUT_CHANNEL.appendLine('Python version: ' + contents['python_version']);
        OUTPUT_CHANNEL.appendLine('Robot Version: ' + contents['robot_version']);
        let env = contents['environment'];
        if (!env) {
            OUTPUT_CHANNEL.appendLine('Environment: NOT received');
        } else {
            // Print some env vars we may care about:
            OUTPUT_CHANNEL.appendLine('Environment:');
            OUTPUT_CHANNEL.appendLine('    PYTHONPATH: ' + env['PYTHONPATH']);
            OUTPUT_CHANNEL.appendLine('    APPDATA: ' + env['APPDATA']);
            OUTPUT_CHANNEL.appendLine('    HOMEDRIVE: ' + env['HOMEDRIVE']);
            OUTPUT_CHANNEL.appendLine('    HOMEPATH: ' + env['HOMEPATH']);
            OUTPUT_CHANNEL.appendLine('    HOME: ' + env['HOME']);
            OUTPUT_CHANNEL.appendLine('    ROBOT_ROOT: ' + env['ROBOT_ROOT']);
            OUTPUT_CHANNEL.appendLine('    ROBOT_ARTIFACTS: ' + env['ROBOT_ARTIFACTS']);
            OUTPUT_CHANNEL.appendLine('    RCC_INSTALLATION_ID: ' + env['RCC_INSTALLATION_ID']);
            OUTPUT_CHANNEL.appendLine('    ROBOCORP_HOME: ' + env['ROBOCORP_HOME']);
            OUTPUT_CHANNEL.appendLine('    PROCESSOR_ARCHITECTURE: ' + env['PROCESSOR_ARCHITECTURE']);
            OUTPUT_CHANNEL.appendLine('    OS: ' + env['OS']);
            OUTPUT_CHANNEL.appendLine('    PATH: ' + env['PATH']);
        }
        if (verifyFileExists(pythonExe)) {
            return {
                pythonExe: pythonExe,
                environ: contents['environment'],
                additionalPythonpathEntries: [],
            };
        }
        return disabled('Python executable: ' + pythonExe + ' does not exist.');
    } catch (error) {
        return disabled('Unable to get python to launch language server.\nStderr: ' + result.stderr + '\nStdout (json contents): ' + result.stdout);
    }
}
