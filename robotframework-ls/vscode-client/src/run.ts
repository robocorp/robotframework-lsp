import {
    commands,
    debug,
    DebugConfiguration,
    DebugSessionOptions,
    ExtensionContext,
    TextEditor,
    Uri,
    window,
    workspace,
    WorkspaceFolder,
} from "vscode";
import { logError, OUTPUT_CHANNEL } from "./channel";
import * as path from "path";
import { parse } from "jsonc-parser";
import * as fs from "fs";

interface ITestInfo {
    uri: string;
    path: string;
    name: string; // if '*' it means that it should run all tests in the path.
}

export async function robotRun(params?: ITestInfo) {
    try {
        await _debug(params, true);
    } catch (error) {
        logError("Error running robot.", error, "RUN_ROBOT_RUN");
    }
}

export async function robotDebug(params?: ITestInfo) {
    try {
        await _debug(params, false);
    } catch (error) {
        logError("Error debugging robot.", error, "RUN_ROBOT_DEBUG");
    }
}

export async function robotRunSuite(resource: Uri) {
    await _debugSuite(resource, true);
}

export async function robotDebugSuite(resource: Uri) {
    await _debugSuite(resource, false);
}

async function checkFileExists(file) {
    return fs.promises
        .access(file, fs.constants.F_OK)
        .then(() => true)
        .catch(() => false);
}

async function readLaunchTemplate(workspaceFolder: WorkspaceFolder): Promise<DebugConfiguration | undefined> {
    const launch = workspace.getConfiguration("launch", workspaceFolder.uri);
    const launchConfigurations = launch.inspect<DebugConfiguration[]>("configurations");
    if (launchConfigurations) {
        const entries: [string, DebugConfiguration[] | undefined][] = [
            ["Workspace Folder Language Value", launchConfigurations.workspaceFolderLanguageValue],
            ["Workspace Folder Value", launchConfigurations.workspaceFolderValue],

            ["Workspace Language Value", launchConfigurations.workspaceLanguageValue],
            ["Workspace Value", launchConfigurations.workspaceValue],

            ["Global Language Value", launchConfigurations.globalLanguageValue],
            ["Global Value", launchConfigurations.globalValue],
        ];
        for (const entry of entries) {
            let configs: DebugConfiguration[] | undefined = entry[1];
            if (configs) {
                for (const cfg of configs) {
                    OUTPUT_CHANNEL.appendLine(`Found ${entry[0]} configuration: ${cfg.type} - ${cfg.name}.`);
                    if (
                        cfg.type == "robotframework-lsp" &&
                        cfg.name &&
                        cfg.name.toLowerCase() == "robot framework: launch template"
                    ) {
                        OUTPUT_CHANNEL.appendLine(`-- matched as launch template.`);
                        return cfg as DebugConfiguration;
                    }
                }
            }
        }
    } else {
        OUTPUT_CHANNEL.appendLine(
            'Did not find any launch configuration when searching for the "Robot Framework: Launch Template".'
        );
    }
    return undefined;
}

async function _debugSuite(resource: Uri | undefined, noDebug: boolean) {
    try {
        if (!resource) {
            // i.e.: collect the tests from the file and ask which one to run.
            let activeTextEditor: TextEditor | undefined = window.activeTextEditor;
            if (!activeTextEditor) {
                window.showErrorMessage("Can only run a test/task suite if the related file is currently opened.");
                return;
            }
            resource = activeTextEditor.document.uri;
        }
        await _debug({ "uri": resource.toString(), "path": resource.fsPath, "name": "*" }, noDebug);
    } catch (error) {
        logError("Error debugging suite.", error, "RUN_DEBUG_SUITE");
    }
}

async function _debug(params: ITestInfo | undefined, noDebug: boolean) {
    let executeUri: Uri;
    let executePath: string;
    let executeName: string;

    if (!params) {
        // i.e.: collect the tests from the file and ask which one to run.
        let activeTextEditor: TextEditor | undefined = window.activeTextEditor;
        if (!activeTextEditor) {
            window.showErrorMessage("Can only run a test/task if the related file is currently opened.");
            return;
        }
        let uri = activeTextEditor.document.uri;
        let tests: [ITestInfo] = await commands.executeCommand("robot.listTests", { "uri": uri.toString() });
        if (!tests) {
            window.showErrorMessage("No tests/tasks found in the currently opened editor.");
            return;
        }

        executeUri = uri;
        executePath = uri.fsPath;

        if (tests.length == 1) {
            executeName = tests[0].name;
        } else {
            let items: string[] = [];
            for (const el of tests) {
                items.push(el.name);
            }
            let selectedItem = await window.showQuickPick(items, {
                "canPickMany": false,
                "placeHolder": "Please select Test / Task to run.",
                "ignoreFocusOut": true,
            });
            if (!selectedItem) {
                return;
            }
            executeName = selectedItem;
        }
    } else {
        executeUri = Uri.file(params.path);
        executePath = params.path;
        executeName = params.name;
    }

    let workspaceFolder = workspace.getWorkspaceFolder(executeUri);
    if (!workspaceFolder) {
        let folders = workspace.workspaceFolders;
        if (folders) {
            // Use the currently opened folder.
            workspaceFolder = folders[0];
        }
    }

    let cwd: string;
    let launchTemplate: DebugConfiguration = undefined;
    if (workspaceFolder) {
        cwd = workspaceFolder.uri.fsPath;
        launchTemplate = await readLaunchTemplate(workspaceFolder);
    } else {
        cwd = path.dirname(executePath);
    }

    let args: string[];
    if (executeName == "*") {
        args = [];
    } else {
        args = ["-t", executeName];
    }

    let debugConfiguration: DebugConfiguration = {
        "type": "robotframework-lsp",
        "name": "Robot Framework: Launch " + executeName,
        "request": "launch",
        "cwd": cwd,
        "target": executePath,
        "terminal": "integrated",
        "env": {},
        "args": args,
    };

    if (launchTemplate) {
        for (var key of Object.keys(launchTemplate)) {
            if (key !== "type" && key !== "name" && key !== "request") {
                let value = launchTemplate[key];
                if (value !== undefined) {
                    if (key === "args") {
                        try {
                            debugConfiguration.args = debugConfiguration.args.concat(value);
                        } catch (err) {
                            logError(
                                "Unable to concatenate: " + debugConfiguration.args + " to: " + value,
                                err,
                                "RUN_CONCAT_ARGS"
                            );
                        }
                    } else {
                        debugConfiguration[key] = value;
                    }
                }
            }
        }
    }

    let debugSessionOptions: DebugSessionOptions = { "noDebug": noDebug };
    debug.startDebugging(workspaceFolder, debugConfiguration, debugSessionOptions);
}

export async function registerRunCommands(context: ExtensionContext) {
    context.subscriptions.push(commands.registerCommand("robot.runTest", robotRun));
    context.subscriptions.push(commands.registerCommand("robot.debugTest", robotDebug));
    context.subscriptions.push(commands.registerCommand("robot.runSuite", robotRunSuite));
    context.subscriptions.push(commands.registerCommand("robot.debugSuite", robotDebugSuite));
}
