"use strict";

import * as vscode from "vscode";
import { expandVars, getArrayStrFromConfigExpandingVars, getStrFromConfigExpandingVars } from "./expandVars";
import {
    workspace,
    window,
    commands,
    DebugConfiguration,
    WorkspaceFolder,
    CancellationToken,
    DebugConfigurationProvider,
    debug,
    DebugAdapterExecutable,
} from "vscode";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { lastLanguageServerExecutable } from "./extension";
import * as path from "path";
import * as fs from "fs";

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

interface InterpreterInfo {
    pythonExe: string;
    environ?: { [key: string]: string };
    additionalPythonpathEntries: string[];
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

export function registerDebugger() {
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
