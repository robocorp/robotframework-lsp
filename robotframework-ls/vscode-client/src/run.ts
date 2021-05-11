import { commands, debug, DebugConfiguration, DebugSessionOptions, ExtensionContext, TextEditor, Uri, window, workspace } from "vscode";
import { OUTPUT_CHANNEL } from "./extension";
import * as path from 'path';

interface ITestInfo {
    uri: string
    path: string
    name: string
}

export async function robotRun(params?: ITestInfo) {
    try {
        await _debug(params, true);
    } catch (error) {
        OUTPUT_CHANNEL.appendLine(error)
    }
}

export async function robotDebug(params?: ITestInfo) {
    try {
        await _debug(params, false);
    } catch (error) {
        OUTPUT_CHANNEL.appendLine(error)
    }
}

async function _debug(params: ITestInfo | undefined, noDebug: boolean) {
    let executeUri: Uri
    let executePath: string
    let executeNames: string[]

    if (!params) {
        // i.e.: collect the tests from the file and ask which one to run.
        let activeTextEditor: TextEditor | undefined = window.activeTextEditor;
        if (!activeTextEditor) {
            window.showErrorMessage('Can only run a test/task if the related file is currently opened.');
            return;
        }
        let uri = activeTextEditor.document.uri;
        let tests: [ITestInfo] = await commands.executeCommand('robot.listTests', { 'uri': uri.toString() });
        if (!tests) {
            window.showErrorMessage('No tests/tasks found in the currently opened editor.');
            return;
        }

        executeUri = uri;
        executePath = uri.fsPath;

        if (tests.length == 1) {
            executeNames = [tests[0].name];

        } else {
            let items: string[] = [];
            for (const el of tests) {
                items.push(el.name);
            }
            let selectedItem = await window.showQuickPick(
                items,
                {
                    // The code is done so that could pick many, but the UI is horrible, 
                    // presenting a list of checkboxes instead of allowing to select based
                    // on the selection / quick filtering, so, just leave it without picking many.
                    "canPickMany": false,
                    'placeHolder': 'Please select Test / Task to run.',
                    'ignoreFocusOut': true,
                }
            );
            if (!selectedItem) {
                return;
            }
            executeNames = [selectedItem];
        }
    } else {
        executeUri = Uri.file(params.path);
        executePath = params.path;
        executeNames = [params.name];
    }

    let workspaceFolder = workspace.getWorkspaceFolder(executeUri);
    let cwd: string;
    if (workspaceFolder) {
        cwd = workspaceFolder.uri.fsPath;
    } else {
        cwd = path.dirname(executePath);
    }

    let args: string[] = [];
    for (const name of executeNames) {
        args.push('-t');
        args.push(name);
    }

    let debugConfiguration: DebugConfiguration = {
        "type": "robotframework-lsp",
        "name": "Robot Framework: Launch " + executeNames.join(', '),
        "request": "launch",
        "cwd": cwd,
        "target": executePath,
        "terminal": "none",
        "env": {},
        "args": args,
    };
    let debugSessionOptions: DebugSessionOptions = { "noDebug": noDebug };
    debug.startDebugging(workspaceFolder, debugConfiguration, debugSessionOptions)
}

export async function registerRunCommands(context: ExtensionContext) {
    context.subscriptions.push(commands.registerCommand('robot.run', robotRun));
    context.subscriptions.push(commands.registerCommand('robot.debug', robotDebug));
}