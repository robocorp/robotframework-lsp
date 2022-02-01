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

"use strict";

import * as net from "net";
import * as path from "path";
import * as fs from "fs";
import * as vscode from "vscode";
import * as cp from "child_process";

import {
    workspace,
    ExtensionContext,
    window,
    commands,
    ConfigurationTarget,
    debug,
    DebugAdapterExecutable,
    DebugConfiguration,
    WorkspaceFolder,
    CancellationToken,
    DebugConfigurationProvider,
    extensions,
} from "vscode";
import { LanguageClientOptions, State } from "vscode-languageclient";
import { LanguageClient, ServerOptions } from "vscode-languageclient/node";
import { ProgressReport, handleProgressMessage } from "./progress";
import { Timing } from "./time";
import { registerRunCommands } from "./run";
import { registerLinkProviders } from "./linkProvider";
import { expandVars, getArrayStrFromConfigExpandingVars, getStrFromConfigExpandingVars } from "./expandVars";
import { registerInteractiveCommands } from "./interactive/rfInteractive";
import { errorFeedback, logError, OUTPUT_CHANNEL } from "./channel";
import { Mutex } from "./mutex";
import { fileExists } from "./files";
import { clearTestItems, handleTestsCollected, ITestInfoFromUri, setupTestExplorerSupport } from "./testview";
import { getPythonExtensionExecutable } from "./pythonExtIntegration";

interface ExecuteWorkspaceCommandArgs {
    command: string;
    arguments: any;
}

function createClientOptions(initializationOptions: object): LanguageClientOptions {
    const clientOptions: LanguageClientOptions = {
        documentSelector: ["robotframework"],
        synchronize: {
            configurationSection: ["robot", "robocorp.home"],
        },
        outputChannel: OUTPUT_CHANNEL,
        initializationOptions: initializationOptions,
    };
    return clientOptions;
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

function removeEscaping(s) {
    if (s instanceof Array) {
        let ret = [];
        for (const it of s) {
            ret.push(removeEscaping(it));
        }
        return ret;
    }

    let str: string = s;

    if (str.startsWith('^"\\') && str.endsWith('"')) {
        str = str.substring(3, str.length - 1);
    } else if (str.startsWith('^"') && str.endsWith('"')) {
        str = str.substring(2, str.length - 1);
    } else if (str.startsWith('"') && str.endsWith('"')) {
        str = str.substring(1, str.length - 1);
    }
    return str;
}

class RobotDebugConfigurationProvider implements DebugConfigurationProvider {
    provideDebugConfigurations?(folder: WorkspaceFolder | undefined, token?: CancellationToken): DebugConfiguration[] {
        let configurations: DebugConfiguration[] = [];
        configurations.push({
            "type": "robotframework-lsp",
            "name": "Robot Framework: Launch .robot file",
            "request": "launch",
            "cwd": '^"\\${workspaceFolder}"',
            "target": '^"\\${file}"',
            "terminal": "integrated",
            "env": {},
            "args": [],
        });
        return configurations;
    }

    async resolveDebugConfigurationWithSubstitutedVariables(
        folder: WorkspaceFolder | undefined,
        debugConfiguration: DebugConfiguration,
        token?: CancellationToken
    ): Promise<DebugConfiguration> {
        // When we resolve a configuration we add the pythonpath and variables to the command line.
        let args: Array<string> = debugConfiguration.args;
        let config = workspace.getConfiguration("robot");
        let pythonpath: Array<string> = getArrayStrFromConfigExpandingVars(config, "pythonpath");
        let variables: object = config.get("variables");
        debugConfiguration.target = removeEscaping(debugConfiguration.target);
        let targetRobot: any = debugConfiguration.target;
        if (targetRobot instanceof Array && targetRobot.length > 0) {
            targetRobot = targetRobot[0];
        }

        // If it's not specified in the language, let's check if some plugin wants to provide an implementation.
        let interpreter: InterpreterInfo = await commands.executeCommand("robot.resolveInterpreter", targetRobot);
        if (interpreter) {
            pythonpath = pythonpath.concat(interpreter.additionalPythonpathEntries);

            if (interpreter.environ) {
                if (!debugConfiguration.env) {
                    debugConfiguration.env = interpreter.environ;
                } else {
                    for (let key of Object.keys(interpreter.environ)) {
                        debugConfiguration.env[key] = interpreter.environ[key];
                    }
                }
            }
            // Also, overridde env variables in the launch config.
            try {
                let newEnv: { [key: string]: string } | "cancelled" = await commands.executeCommand(
                    "robocorp.updateLaunchEnv",
                    {
                        "targetRobot": targetRobot,
                        "env": debugConfiguration.env,
                    }
                );
                if (newEnv == "cancelled") {
                    OUTPUT_CHANNEL.appendLine("Launch cancelled");
                    return undefined;
                }

                debugConfiguration.env = newEnv;
            } catch (error) {
                // The command may not be available.
            }
        }

        let newArgs = [];
        pythonpath.forEach((element) => {
            newArgs.push("--pythonpath");
            newArgs.push(element);
        });

        for (let key in variables) {
            if (variables.hasOwnProperty(key)) {
                newArgs.push("--variable");
                newArgs.push(key + ":" + expandVars(variables[key]));
            }
        }
        if (args) {
            args = args.concat(newArgs);
        } else {
            args = newArgs;
        }
        debugConfiguration.args = args;

        let uri = vscode.Uri.file(targetRobot);
        let wsFolder = workspace.getWorkspaceFolder(uri);
        if (!wsFolder) {
            wsFolder = folder;
        }
        if (debugConfiguration.cwd) {
            debugConfiguration.cwd = removeEscaping(debugConfiguration.cwd);

            let stat: vscode.FileStat;
            try {
                stat = await vscode.workspace.fs.stat(vscode.Uri.file(debugConfiguration.cwd));
            } catch (err) {
                window.showErrorMessage(
                    "Unable to launch. Reason: the cwd: " + debugConfiguration.cwd + " does not exist."
                );
                return undefined;
            }
            if ((stat.type | vscode.FileType.File) == 1) {
                window.showErrorMessage(
                    "Unable to launch. Reason: the cwd: " +
                        debugConfiguration.cwd +
                        " seems to be a file and not a directory."
                );
                return undefined;
            }
        } else {
            if (wsFolder) {
                debugConfiguration.cwd = wsFolder?.uri?.fsPath;
            }
        }
        return debugConfiguration;
    }
}

interface InterpreterInfo {
    pythonExe: string;
    environ?: { [key: string]: string };
    additionalPythonpathEntries: string[];
}

function registerDebugger() {
    async function createDebugAdapterExecutable(
        env: { [key: string]: string },
        targetRobot: string
    ): Promise<DebugAdapterExecutable> {
        let dapPythonExecutable: string[] | undefined = undefined;
        const inConfig: string = getStrFromConfigExpandingVars(
            workspace.getConfiguration("robot"),
            "python.executable"
        );
        if (inConfig) {
            dapPythonExecutable = [inConfig];
        }

        // Even if it's specified in the language, let's check if some plugin wants to provide an implementation.
        const interpreter: InterpreterInfo = await commands.executeCommand("robot.resolveInterpreter", targetRobot);
        if (interpreter) {
            dapPythonExecutable = [interpreter.pythonExe];
            if (interpreter.environ) {
                if (!env) {
                    env = interpreter.environ;
                } else {
                    for (let key of Object.keys(interpreter.environ)) {
                        env[key] = interpreter.environ[key];
                    }
                }
            }
        } else if ((!dapPythonExecutable || dapPythonExecutable.length === 0) && env) {
            // If a `PYTHON_EXE` is specified in the env, give it priority vs using the language server
            // executable.
            const inEnv = env["PYTHON_EXE"];
            if (inEnv) {
                dapPythonExecutable = [inEnv];
            }
        }

        if (!dapPythonExecutable || dapPythonExecutable.length === 0) {
            // If the dapPythonExecutable is not specified, use the default language server executable.
            if (!lastLanguageServerExecutable) {
                window.showWarningMessage(
                    "Error getting language server python executable for creating a debug adapter."
                );
                return;
            }
            dapPythonExecutable = lastLanguageServerExecutable;
        }

        if (!dapPythonExecutable || dapPythonExecutable.length === 0) {
            window.showWarningMessage("Error. Unable to resolve the python executable to launch debug adapter.");
            return;
        }

        const targetMain: string = path.resolve(__dirname, "../../src/robotframework_debug_adapter/__main__.py");
        if (!fs.existsSync(targetMain)) {
            window.showWarningMessage("Error. Expected: " + targetMain + " to exist.");
            return;
        }
        if (!fs.existsSync(dapPythonExecutable[0])) {
            window.showWarningMessage("Error. Expected: " + dapPythonExecutable[0] + " to exist.");
            return;
        }

        OUTPUT_CHANNEL.appendLine("Launching debug adapter with python: " + dapPythonExecutable);

        const args = [];
        for (let index = 1; index < dapPythonExecutable.length; index++) {
            args.push(dapPythonExecutable[index]);
        }
        args.push("-u");
        args.push(targetMain);
        if (env) {
            return new DebugAdapterExecutable(dapPythonExecutable[0], args, { "env": env });
        } else {
            return new DebugAdapterExecutable(dapPythonExecutable[0], args);
        }
    }

    try {
        debug.registerDebugConfigurationProvider("robotframework-lsp", new RobotDebugConfigurationProvider());

        debug.registerDebugAdapterDescriptorFactory("robotframework-lsp", {
            createDebugAdapterDescriptor: (session) => {
                let env = session.configuration.env;
                let target = session.configuration.target;
                return createDebugAdapterExecutable(env, target);
            },
        });
    } catch (error) {
        // i.e.: https://github.com/microsoft/vscode/issues/118562
        logError("Error registering debugger.", error, "EXT_REGISTER_DEBUGGER");
    }
}

interface ExecutableAndMessage {
    executable: string[] | undefined;
    message: string;
}

async function getDefaultLanguageServerPythonExecutable(): Promise<ExecutableAndMessage> {
    OUTPUT_CHANNEL.appendLine("Getting language server Python executable.");
    const languageServerPython: string = getStrFromConfigExpandingVars(
        workspace.getConfiguration("robot"),
        "language-server.python"
    );

    if (languageServerPython) {
        if (languageServerPython.indexOf("/") !== -1 || languageServerPython.indexOf("\\") !== -1) {
            // This means it was specified as a full path and it's not just a basename.
            if (!fs.existsSync(languageServerPython)) {
                return {
                    executable: undefined,
                    "message":
                        "Unable to start robotframework-lsp because: " +
                        languageServerPython +
                        " (specified as robot.language-server.python) does not exist. Do you want to select a new python executable to start robotframework-lsp?",
                };
            }
            return {
                executable: [languageServerPython],
                "message": undefined,
            };
        } else {
            // Just basename was specified: we need to find it in the PATH
            OUTPUT_CHANNEL.appendLine(
                "Language server Python executable: searching " + languageServerPython + " in the PATH."
            );
            const found = findExecutableInPath(languageServerPython);
            if (!found) {
                OUTPUT_CHANNEL.appendLine(
                    "Language server Python executable: could not find: " + languageServerPython + " in the PATH."
                );
                return {
                    executable: undefined,
                    "message":
                        "Unable to start robotframework-lsp because: " +
                        languageServerPython +
                        " could not be found in the PATH. Do you want to select a python executable to start robotframework-lsp?",
                };
            }
            OUTPUT_CHANNEL.appendLine("Language server Python executable: found: " + found);
            return {
                executable: [found],
                "message": undefined,
            };
        }
    }

    // If we got here, it means that the language server python executable wasn't specified,
    // so, we'll use some additional heuristics...

    // Try to use the Robocorp Code extension to provide one for us (if it's installed and
    // available).
    try {
        const languageServerPython: string = await commands.executeCommand<string>("robocorp.getLanguageServerPython");
        if (languageServerPython) {
            OUTPUT_CHANNEL.appendLine(
                "Language server Python executable gotten from robocorp.getLanguageServerPython."
            );
            return {
                executable: [languageServerPython],
                "message": undefined,
            };
        }
    } catch (error) {
        // The command may not be available (in this case, go forward and try to find it in the filesystem).
    }

    // If the user hasn't defined an executable, try to see if we can get it
    // from the python installation.
    let executableAsArray: string[] | undefined = await getPythonExtensionExecutable();
    if (executableAsArray && executableAsArray.length > 0) {
        OUTPUT_CHANNEL.appendLine("Using ms-python.python returned python executable: " + executableAsArray);
        return {
            executable: executableAsArray,
            "message": undefined,
        };
    }

    // Search python from the path.
    OUTPUT_CHANNEL.appendLine("Language server Python executable: searching in PATH.");
    if (process.platform == "win32") {
        const executable = findExecutableInPath("python.exe");
        if (!executable) {
            return {
                executable: undefined,
                "message":
                    "Unable to start robotframework-lsp because: python.exe could not be found in the PATH. Do you want to select a python executable to start robotframework-lsp?",
            };
        }
        OUTPUT_CHANNEL.appendLine("Language server Python executable: found in PATH: " + executable);
        return {
            executable: [executable],
            "message": undefined,
        };
    } else {
        // Not Windows
        let executable = findExecutableInPath("python3");
        if (!executable) {
            executable = findExecutableInPath("python");
        }
        if (!executable) {
            return {
                executable: undefined,
                "message":
                    "Unable to start robotframework-lsp because: neither python3 nor python could be found in the PATH. Do you want to select a python executable to start robotframework-lsp?",
            };
        }
        OUTPUT_CHANNEL.appendLine("Language server Python executable: found in PATH: " + executable);
        return {
            executable: [executable],
            "message": undefined,
        };
    }
}

/**
 * This function is responsible for collecting the needed settings and then
 * starting the language server process (or connecting to the specified
 * tcp port).
 */
const serverOptions: ServerOptions = async function () {
    let executableAndMessage: ExecutableAndMessage = await getDefaultLanguageServerPythonExecutable();
    if (executableAndMessage.message) {
        OUTPUT_CHANNEL.appendLine(executableAndMessage.message);

        let saveInUser: string = "Yes (save in user settings)";
        let saveInWorkspace: string = "Yes (save in workspace settings)";

        let selection = await window.showWarningMessage(
            executableAndMessage.message,
            ...[saveInUser, saveInWorkspace, "No"]
        );
        // robot.language-server.python
        if (selection == saveInUser || selection == saveInWorkspace) {
            let onfulfilled = await window.showOpenDialog({
                "canSelectMany": false,
                "openLabel": "Select python exe",
            });
            if (!onfulfilled || onfulfilled.length == 0) {
                // There's not much we can do (besides start listening to changes to the related variables
                // on the finally block so that we start listening and ask for a reload if a related configuration changes).
                let msg = "Unable to start (python selection cancelled).";
                OUTPUT_CHANNEL.appendLine(msg);
                throw new Error(msg);
            }

            let configurationTarget: ConfigurationTarget;
            if (selection == saveInUser) {
                configurationTarget = ConfigurationTarget.Global;
            } else {
                configurationTarget = ConfigurationTarget.Workspace;
            }

            let config = workspace.getConfiguration("robot");
            try {
                config.update("language-server.python", onfulfilled[0].fsPath, configurationTarget);
            } catch (err) {
                let errorMessage = "Error persisting python to start the language server.\nError: " + err.message;
                logError("Error persisting python to start the language server.", err, "EXT_SAVE_LS_PYTHON");

                if (configurationTarget == ConfigurationTarget.Workspace) {
                    try {
                        config.update("language-server.python", onfulfilled[0].fsPath, ConfigurationTarget.Global);
                        window.showInformationMessage(
                            "It was not possible to save the configuration in the workspace. It was saved in the user settings instead."
                        );
                        err = undefined;
                    } catch (err2) {
                        // ignore this one (show original error).
                    }
                }
                if (err !== undefined) {
                    window.showErrorMessage(errorMessage);
                }
            }
            executableAndMessage = { "executable": [onfulfilled[0].fsPath], message: undefined };
        } else {
            // There's not much we can do (besides start listening to changes to the related variables
            // on the finally block so that we start listening and ask for a reload if a related configuration changes).
            // At this point, already start listening for changes to reload.
            let msg = "Unable to start (no python executable specified).";
            OUTPUT_CHANNEL.appendLine(msg);
            errorFeedback("EXT_NO_PYEXE");
            throw new Error(msg);
        }
    }

    // Note: we need it even in the case we're connecting to a socket (to make launches with the DAP).
    lastLanguageServerExecutable = executableAndMessage.executable;

    let port: number = workspace.getConfiguration("robot").get<number>("language-server.tcp-port");
    if (port) {
        OUTPUT_CHANNEL.appendLine("Connecting to port: " + port);
        var client = new net.Socket();
        return await new Promise((resolve, reject) => {
            client.connect(port, "127.0.0.1", function () {
                resolve({
                    reader: client,
                    writer: client,
                });
            });
        });
    } else {
        let targetMain: string = path.resolve(__dirname, "../../src/robotframework_ls/__main__.py");
        if (!fs.existsSync(targetMain)) {
            let msg = `Error. Expected: ${targetMain} to exist.`;
            window.showWarningMessage(msg);
            errorFeedback("EXT_NO_MAIN");
            throw new Error(msg);
        }

        let args: Array<string> = [];
        for (let index = 1; index < executableAndMessage.executable.length; index++) {
            args.push(executableAndMessage.executable[index]);
        }
        args.push("-u");
        args.push(targetMain);
        let lsArgs = workspace.getConfiguration("robot").get<Array<string>>("language-server.args");
        if (lsArgs && !(lsArgs instanceof Array)) {
            OUTPUT_CHANNEL.appendLine(
                "Ignoring robot.language-server.args because it's not an array. Found: " + lsArgs
            );
            lsArgs = undefined;
        }
        if (lsArgs && lsArgs.length >= 1) {
            args = args.concat(lsArgs);
        } else {
            // Default is using simple verbose mode (shows critical/info but not debug).
            args.push("-v");
        }
        OUTPUT_CHANNEL.appendLine(
            "Starting RobotFramework Language Server with args: " + executableAndMessage.executable[0] + "," + args
        );

        let src: string = path.resolve(__dirname, "../../src");
        const serverProcess = cp.spawn(executableAndMessage.executable[0], args, {
            env: { ...process.env, PYTHONPATH: src },
        });
        if (!serverProcess || !serverProcess.pid) {
            throw new Error(
                `Launching server using command ${executableAndMessage.executable[0]} with args: ${args} failed.`
            );
        }
        return serverProcess;
    }
};

/**
 * Registers listeners which should act on $/customProgress and $/executeWorkspaceCommand.
 */
async function registerLanguageServerListeners(langServer: LanguageClient) {
    let stopListeningOnDidChangeState = langServer.onDidChangeState((event) => {
        if (event.newState == State.Running) {
            // i.e.: We need to register the customProgress as soon as it's running (we can't wait for onReady)
            // because at that point if there are open documents, lots of things may've happened already, in
            // which case the progress won't be shown on some cases where it should be shown.
            extensionContext.subscriptions.push(
                langServer.onNotification("$/customProgress", (args: ProgressReport) => {
                    // OUTPUT_CHANNEL.appendLine(args.id + ' - ' + args.kind + ' - ' + args.title + ' - ' + args.message + ' - ' + args.increment);
                    handleProgressMessage(args);
                })
            );

            extensionContext.subscriptions.push(
                langServer.onNotification("$/testsCollected", (args: ITestInfoFromUri) => {
                    handleTestsCollected(args);
                })
            );
            extensionContext.subscriptions.push(
                langServer.onRequest("$/executeWorkspaceCommand", async (args: ExecuteWorkspaceCommandArgs) => {
                    // OUTPUT_CHANNEL.appendLine(args.command + " - " + args.arguments);
                    let ret;
                    try {
                        ret = await commands.executeCommand(args.command, args.arguments);
                    } catch (err) {
                        if (!(err.message && err.message.endsWith("not found"))) {
                            // Log if the error wasn't that the command wasn't found
                            logError("Error executing workspace command.", err, "EXT_EXECUTE_WS_COMMAND");
                        }
                    }
                    return ret;
                })
            );
            // Note: don't dispose (we need to re-register on a restart).
            // stopListeningOnDidChangeState.dispose();
        }
    });
}

async function startLanguageServer(): Promise<LanguageClient> {
    let timing = new Timing();
    let langServer: LanguageClient;
    let initializationOptions: object = {};
    try {
        let pluginsDir: string = await commands.executeCommand<string>("robocorp.getPluginsDir");
        try {
            if (pluginsDir && pluginsDir.length > 0) {
                OUTPUT_CHANNEL.appendLine("Plugins dir: " + pluginsDir + ".");
                initializationOptions["pluginsDir"] = pluginsDir;
            }
        } catch (error) {
            logError("Error setting pluginsDir.", error, "EXT_PLUGINS_DIR");
        }
    } catch (error) {
        // The command may not be available.
    }

    langServer = new LanguageClient(
        "Robot Framework Language Server",
        serverOptions,
        createClientOptions(initializationOptions)
    );

    await setupTestExplorerSupport();
    // Important: register listeners before starting (otherwise startup progress is not shown).
    await registerLanguageServerListeners(langServer);

    extensionContext.subscriptions.push(langServer.start());

    // i.e.: if we return before it's ready, the language server commands
    // may not be available.
    OUTPUT_CHANNEL.appendLine("Waiting for RobotFramework (python) Language Server to finish activating...");
    await langServer.onReady();
    // ask it to start indexing only after ready.
    commands.executeCommand("robot.startIndexing.internal");

    let version = extensions.getExtension("robocorp.robotframework-lsp").packageJSON.version;
    try {
        let lsVersion = await commands.executeCommand("robot.getLanguageServerVersion");
        if (lsVersion != version) {
            window.showErrorMessage(
                "Error: expected robotframework-lsp version: " +
                    version +
                    ". Found: " +
                    lsVersion +
                    "." +
                    " Please uninstall the older version from the python environment."
            );
        }
    } catch (err) {
        let msg =
            "Error: robotframework-lsp version mismatch. Please uninstall the older version from the python environment.";
        logError(msg, err, "EXT_VERSION_MISMATCH");
        window.showErrorMessage(msg);
    }

    OUTPUT_CHANNEL.appendLine("RobotFramework Language Server ready. Took: " + timing.getTotalElapsedAsStr());
    return langServer;
}

export let languageServerClient: LanguageClient | undefined = undefined;
let languageServerClientMutex: Mutex = new Mutex();
let extensionContext: ExtensionContext | undefined = undefined;
let lastLanguageServerExecutable: string[] | undefined = undefined;

async function restartLanguageServer() {
    await languageServerClientMutex.dispatch(async () => {
        let title = "Robot Framework Language Server loading ...";
        if (languageServerClient !== undefined) {
            title = "Robot Framework Language Server reloading ...";
        }
        await window.withProgress(
            {
                location: vscode.ProgressLocation.Window,
                title: title,
                cancellable: false,
            },
            async () => {
                if (languageServerClient !== undefined) {
                    try {
                        // In this case, just restart (it should get the new settings automatically).
                        let timing = new Timing();
                        OUTPUT_CHANNEL.appendLine("Restarting Robot Framework Language Server.");

                        try {
                            await languageServerClient.stop();
                        } catch (err) {
                            logError("Error stopping language server.", err, "EXT_STOP_ROBOT_LS");
                        }
                        languageServerClient.start();
                        await languageServerClient.onReady();
                        // ask it to start indexing only after ready.
                        commands.executeCommand("robot.startIndexing.internal");
                        OUTPUT_CHANNEL.appendLine(
                            "RobotFramework Language Server restarted. Took: " + timing.getTotalElapsedAsStr()
                        );
                    } catch (err) {
                        logError("Error restarting language server.", err, "EXT_RESTART_ROBOT_LS");
                        // If it fails once it'll never work again -- it seems it caches our failure :(
                        // See: https://github.com/microsoft/vscode-languageserver-node/issues/872
                        window
                            .showWarningMessage(
                                'There was an error reloading the Robot Framework Language Server. Please use the "Reload Window" action to apply the new settings.',
                                ...["Reload Window"]
                            )
                            .then((selection) => {
                                if (selection === "Reload Window") {
                                    commands.executeCommand("workbench.action.reloadWindow");
                                }
                            });
                        return;
                    }

                    window.showInformationMessage("Robot Framework Language Server reloaded with new settings.");
                    return;
                }

                // If we get here, this means it never really did start correctly (hopefully it'll work now with the new settings)...
                try {
                    // Note: assign to module variable.
                    languageServerClient = await startLanguageServer();
                    window.showInformationMessage("Robot Framework Language Server started with the new settings.");
                } catch (err) {
                    const msg =
                        "It was not possible to start the Robot Framework Language Server. Please update the related `robot.language-server` configurations.";
                    logError(msg, err, "EXT_UNABLE_TO_START_2");
                    window.showErrorMessage(msg);
                }
            }
        );
    });
}

async function removeCaches(dirPath: string, level: number, removeDirsArray: string[]) {
    let dirContents = await fs.promises.readdir(dirPath, { withFileTypes: true });

    for await (const dirEnt of dirContents) {
        var entryPath = path.join(dirPath, dirEnt.name);

        if (dirEnt.isDirectory()) {
            await removeCaches(entryPath, level + 1, removeDirsArray);
            removeDirsArray.push(entryPath);
        } else {
            try {
                await fs.promises.unlink(entryPath);
                OUTPUT_CHANNEL.appendLine(`Removed: ${entryPath}.`);
            } catch (err) {
                OUTPUT_CHANNEL.appendLine(`Unable to remove: ${entryPath}. ${err}`);
            }
        }
    }

    if (level === 0) {
        // Remove the (empty) directories only after all iterations finished.
        for (const entryPath of removeDirsArray) {
            try {
                await fs.promises.rmdir(entryPath);
                OUTPUT_CHANNEL.appendLine(`Removed dir: ${entryPath}.`);
            } catch (err) {
                OUTPUT_CHANNEL.appendLine(`Unable to remove dir: ${entryPath}. ${err}`);
            }
        }
    }
}

async function clearCachesAndRestartProcessesStart(): Promise<boolean> {
    if (languageServerClient === undefined) {
        window.showErrorMessage(
            "Unable to clear caches and restart because the language server still hasn't been successfully started."
        );
        return false;
    }
    let homeDir: string;
    try {
        homeDir = await commands.executeCommand("robot.getRFLSHomeDir");
    } catch (err) {
        let msg = "Unable to clear caches and restart because calling robot.getRFLSHomeDir threw an exception.";
        window.showErrorMessage(msg);
        logError(msg, err, "EXT_GET_HOMEDIR");
        return false;
    }

    try {
        await languageServerClient.stop();
    } catch (err) {
        logError("Error stopping language server.", err, "EXT_STOP_LS_ON_CLEAR_RESTART");
    }
    await clearTestItems();
    if (await fileExists(homeDir)) {
        await removeCaches(homeDir, 0, []);
    }
    return true;
}

async function clearCachesAndRestartProcessesFinish() {
    try {
        await languageServerClient.start();

        await languageServerClient.onReady();
        // ask it to start indexing only after ready.
        await commands.executeCommand("robot.startIndexing.internal");
    } catch (err) {
        logError("Error starting language server.", err, "EXT_START_LS_ON_CLEAR_RESTART");
        window
            .showWarningMessage(
                'There was an error reloading the Robot Framework Language Server. Please use the "Reload Window" action to finish restarting the language server.',
                ...["Reload Window"]
            )
            .then((selection) => {
                if (selection === "Reload Window") {
                    commands.executeCommand("workbench.action.reloadWindow");
                }
            });
        return;
    }
}

async function clearCachesAndRestartProcesses() {
    await window.withProgress(
        {
            location: vscode.ProgressLocation.Window,
            title: "Clearing caches and restarting Robot Framework Language Server.",
            cancellable: false,
        },
        async () => {
            let okToRestart = await clearCachesAndRestartProcessesStart();
            if (!okToRestart) {
                return;
            }
            await clearCachesAndRestartProcessesFinish();
            window.showInformationMessage("Caches cleared and Robot Framework Language Server restarted.");
        }
    );
}

function registerOnDidChangeConfiguration(context: ExtensionContext): void {
    context.subscriptions.push(
        workspace.onDidChangeConfiguration((event) => {
            for (let s of [
                "robot.language-server.python",
                "robot.language-server.tcp-port",
                "robot.language-server.args",
            ]) {
                if (event.affectsConfiguration(s)) {
                    restartLanguageServer();
                    break;
                }
            }
        })
    );
}

export async function activate(context: ExtensionContext) {
    extensionContext = context;

    context.subscriptions.push(
        commands.registerCommand("robot.clearCachesAndRestartProcesses", clearCachesAndRestartProcesses)
    );
    context.subscriptions.push(
        commands.registerCommand(
            "robot.clearCachesAndRestartProcesses.start.internal",
            clearCachesAndRestartProcessesStart
        )
    );
    context.subscriptions.push(
        commands.registerCommand(
            "robot.clearCachesAndRestartProcesses.finish.internal",
            clearCachesAndRestartProcessesFinish
        )
    );
    registerDebugger();
    await registerRunCommands(context);
    await registerLinkProviders(context);
    await registerInteractiveCommands(context);

    try {
        // Note: assign to module variable.
        languageServerClient = await startLanguageServer();
    } catch (err) {
        const msg =
            "It was not possible to start the Robot Framework Language Server. Please update the related `robot.language-server` configurations.";
        logError(msg, err, "EXT_UNABLE_TO_START");
        window.showErrorMessage(msg);
    } finally {
        // Note: only register to listen for changes at the end.
        // If we do it before, we conflict with the case where we
        // ask for the executable in a dialog (and then we'd go
        // through the usual start and a restart at the same time).
        registerOnDidChangeConfiguration(context);
    }
}
