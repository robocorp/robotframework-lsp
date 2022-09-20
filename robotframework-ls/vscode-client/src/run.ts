import {
    commands,
    DebugConfiguration,
    ExtensionContext,
    TestItem,
    TestRunRequest,
    TextEditor,
    Uri,
    window,
    workspace,
    WorkspaceFolder,
} from "vscode";
import { logError, OUTPUT_CHANNEL } from "./channel";
import {
    computeTestId,
    computeUriTestId,
    DEBUG_PROFILE,
    getTestItem,
    handleTestsCollected,
    IRange,
    RUN_PROFILE,
} from "./testview";
import { CancellationTokenSource } from "vscode-languageclient";

interface ITestInfo {
    uri: string;
    path: string;
    name: string; // if '*' it means that it should run all tests in the path.
    range: IRange;
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

export async function readLaunchTemplate(workspaceFolder: WorkspaceFolder): Promise<DebugConfiguration | undefined> {
    const launch = workspace.getConfiguration("launch", workspaceFolder);
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
        await _debug({ "uri": resource.toString(), "path": resource.fsPath, "name": "*", "range": undefined }, noDebug);
    } catch (error) {
        logError("Error debugging suite.", error, "RUN_DEBUG_SUITE");
    }
}

async function obtainTestItem(uri: Uri, name: string): Promise<TestItem | undefined> {
    let testId: string;
    let tests: ITestInfo[] = await commands.executeCommand("robot.listTests", { "uri": uri.toString() });
    await handleTestsCollected({ "uri": uri.toString(), "testInfo": tests });

    if (name === "*") {
        testId = computeUriTestId(uri.toString());
    } else {
        testId = computeTestId(uri.toString(), name);
    }
    let testItem = getTestItem(testId);
    if (!testItem) {
        const msg = "Unable to obtain test item from: " + uri + " - " + name;
        OUTPUT_CHANNEL.appendLine(msg);
        window.showErrorMessage(msg);
    }

    return getTestItem(testId);
}

async function _debug(params: ITestInfo | undefined, noDebug: boolean) {
    let executeUri: Uri;
    let executeName: string;

    if (!params) {
        // i.e.: collect the tests from the file and ask which one to run.
        let activeTextEditor: TextEditor | undefined = window.activeTextEditor;
        if (!activeTextEditor) {
            window.showErrorMessage("Can only run a test/task if the related file is currently opened.");
            return;
        }
        let uri = activeTextEditor.document.uri;
        let tests: ITestInfo[] = await commands.executeCommand("robot.listTests", { "uri": uri.toString() });
        if (!tests) {
            window.showErrorMessage("No tests/tasks found in the currently opened editor.");
            return;
        }

        executeUri = uri;

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
        executeName = params.name;
    }

    let include: TestItem[] = [];
    const testItem = await obtainTestItem(executeUri, executeName);
    if (testItem) {
        include.push(testItem);
        const request = new TestRunRequest(include);
        const cancellationTokenSource = new CancellationTokenSource();
        if (noDebug) {
            RUN_PROFILE.runHandler(request, cancellationTokenSource.token);
        } else {
            DEBUG_PROFILE.runHandler(request, cancellationTokenSource.token);
        }
    } else {
        OUTPUT_CHANNEL.appendLine("Could not find test item from: " + executeUri + " - " + executeName);
    }
}

export async function registerRunCommands(context: ExtensionContext) {
    context.subscriptions.push(commands.registerCommand("robot.runTest", robotRun));
    context.subscriptions.push(commands.registerCommand("robot.debugTest", robotDebug));
    context.subscriptions.push(commands.registerCommand("robot.runSuite", robotRunSuite));
    context.subscriptions.push(commands.registerCommand("robot.debugSuite", robotDebugSuite));
}
