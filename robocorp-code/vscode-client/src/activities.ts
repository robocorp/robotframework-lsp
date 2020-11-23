import { commands, window, WorkspaceFolder, workspace, Uri, QuickPickItem, TextEdit, debug, DebugConfiguration, DebugSessionOptions, env, ConfigurationTarget } from "vscode";
import { join } from 'path';
import { OUTPUT_CHANNEL } from './channel';
import * as roboCommands from './robocorpCommands';


interface QuickPickItemWithAction extends QuickPickItem {
    action: any;
    sortKey?: string;
}

interface QuickPickItemRobotTask extends QuickPickItem {
    robotYaml: string;
    taskName: string;
    keyInLRU: string;
}

function sortCaptions(captions: QuickPickItemWithAction[]) {
    captions.sort(function (a, b) {
        if (a.sortKey < b.sortKey) {
            return -1;
        }
        if (a.sortKey > b.sortKey) {
            return 1;
        }

        if (a.label < b.label) {
            return -1;
        }
        if (a.label > b.label) {
            return 1;
        }

        return 0;
    });
}

export async function cloudLogin(): Promise<boolean> {
    let loggedIn: boolean;
    do {
        let credentials: string = await window.showInputBox({
            'password': true,
            'prompt': 'Please provide the access credentials - Confirm without entering any text to open https://cloud.robocorp.com/settings/access-credentials where credentials may be obtained - ',
            'ignoreFocusOut': true,
        });
        if (credentials == undefined) {
            return false;
        }
        if (!credentials) {
            env.openExternal(Uri.parse('https://cloud.robocorp.com/settings/access-credentials'));
            continue;
        }
        loggedIn = await commands.executeCommand(
            roboCommands.ROBOCORP_CLOUD_LOGIN_INTERNAL, { 'credentials': credentials }
        );
        if (!loggedIn) {
            let retry = "Retry with new credentials";
            let selectedItem = await window.showWarningMessage('Unable to log in with the provided credentials.', { 'modal': true }, retry);
            if (!selectedItem) {
                return false;
            }
        }
    } while (!loggedIn);
    return true;
}

async function askRobotSelection(robotsInfo: LocalRobotMetadataInfo[], message: string): Promise<LocalRobotMetadataInfo> {
    let robot: LocalRobotMetadataInfo;
    if (robotsInfo.length > 1) {
        let captions: QuickPickItemWithAction[] = new Array();

        for (let i = 0; i < robotsInfo.length; i++) {
            const element: LocalRobotMetadataInfo = robotsInfo[i];
            let caption: QuickPickItemWithAction = {
                'label': element.name,
                'description': element.directory,
                'action': element
            };
            captions.push(caption);
        }
        let selectedItem: QuickPickItemWithAction = await window.showQuickPick(
            captions,
            {
                "canPickMany": false,
                'placeHolder': message,
                'ignoreFocusOut': true,
            }
        );
        if (!selectedItem) {
            return;
        }
        robot = selectedItem.action;
    } else {
        robot = robotsInfo[0];
    }
    return robot;
}

async function askAndCreateNewRobotAtWorkspace(wsInfo: WorkspaceInfo, directory: string) {
    let robotName: string = await window.showInputBox({
        'prompt': 'Please provide the name for the new Robot.',
        'ignoreFocusOut': true,
    });
    if (!robotName) {
        return;
    }

    let actionResult: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCORP_UPLOAD_TO_NEW_ROBOT_INTERNAL,
        { 'workspaceId': wsInfo.workspaceId, 'directory': directory, 'robotName': robotName }
    );
    if (!actionResult.success) {
        let msg: string = 'Error uploading to new Robot: ' + actionResult.message;
        OUTPUT_CHANNEL.appendLine(msg);
        window.showErrorMessage(msg);
    } else {
        window.showInformationMessage('Successfully submitted new Robot ' + robotName + ' to the cloud.')
    }

}

export async function setPythonInterpreterFromRobotYaml() {
    let actionResult: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );
    if (!actionResult.success) {
        window.showInformationMessage('Error listing existing robots: ' + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage('Unable to set Python extension interpreter (no Robot detected in the Workspace).');
        return;
    }

    let robot: LocalRobotMetadataInfo = await askRobotSelection(robotsInfo, 'Please select the Robot from which the python executable should be used.');
    if (!robot) {
        return;
    }

    try {
        let result: ActionResult = await commands.executeCommand(roboCommands.ROBOCORP_RESOLVE_INTERPRETER, { 'target_robot': robot.filePath });
        if (!result.success) {
            window.showWarningMessage('Error resolving interpreter info: ' + result.message);
            return;
        }
        let interpreter: InterpreterInfo = result.result;
        if (!interpreter || !interpreter.pythonExe) {
            window.showWarningMessage('Unable to obtain interpreter information from: ' + robot.filePath);
            return;
        }

        // Note: if we got here we have a robot in the workspace.
        let selectedItem = await window.showQuickPick(
            ['Workspace Settings', 'Global Settings'],
            {
                "canPickMany": false,
                'placeHolder': 'Please select where the python.pythonPath configuration should be set.',
                'ignoreFocusOut': true,
            }
        );

        if (!selectedItem) {
            return;
        }

        let configurationTarget: ConfigurationTarget = undefined;
        if (selectedItem == 'Global Settings') {
            configurationTarget = ConfigurationTarget.Global;
        } else if (selectedItem == 'Workspace Settings') {
            configurationTarget = ConfigurationTarget.Workspace;
        } else {
            window.showWarningMessage('Invalid configuration target: ' + selectedItem);
            return;
        }

        let config = workspace.getConfiguration('python');
        await config.update('pythonPath', interpreter.pythonExe, configurationTarget);
        window.showInformationMessage('Successfully set python.pythonPath set in: ' + selectedItem);
    } catch (error) {
        window.showWarningMessage('Error setting python.pythonPath configuration: ' + error);
        return;
    }

}


export async function uploadRobot() {

    // Start this in parallel while we ask the user for info.
    let isLoginNeededPromise: Thenable<ActionResult> = commands.executeCommand(
        roboCommands.ROBOCORP_IS_LOGIN_NEEDED_INTERNAL,
    );

    let currentUri: Uri;
    if (window.activeTextEditor && window.activeTextEditor.document) {
        currentUri = window.activeTextEditor.document.uri;
    }
    let actionResult: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );
    if (!actionResult.success) {
        window.showInformationMessage('Error submitting Robot to the cloud: ' + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage('Unable to submit Robot to the cloud (no Robot detected in the Workspace).');
        return;
    }

    let isLoginNeeded: ActionResult = await isLoginNeededPromise;
    if (!isLoginNeeded) {
        window.showInformationMessage('Error getting if login is needed.');
        return;
    }

    if (isLoginNeeded.result) {
        let loggedIn: boolean = await cloudLogin();
        if (!loggedIn) {
            return;
        }
    }

    let robot: LocalRobotMetadataInfo = await askRobotSelection(robotsInfo, 'Please select the Robot to upload to the Cloud.');
    if (!robot) {
        return;
    }

    let refresh = false;
    SELECT_OR_REFRESH:
    do {
        // We ask for the information on the existing workspaces information.
        // Note that this may be cached from the last time it was asked, 
        // so, we have an option to refresh it (and ask again).
        let actionResult: ListWorkspacesActionResult = await commands.executeCommand(
            roboCommands.ROBOCORP_CLOUD_LIST_WORKSPACES_INTERNAL, { 'refresh': refresh }
        );

        if (!actionResult.success) {
            window.showErrorMessage('Error listing cloud workspaces: ' + actionResult.message);
            return;
        }

        let workspaceInfo: WorkspaceInfo[] = actionResult.result;
        if (!workspaceInfo || workspaceInfo.length == 0) {
            window.showErrorMessage('A Cloud Workspace must be created to submit a Robot to the cloud.');
            return;
        }

        // Now, if there are only a few items or a single workspace,
        // just show it all, otherwise do a pre-selectedItem with the workspace.
        let workspaceIdFilter: string = undefined;

        if (workspaceInfo.length > 1) {
            // Ok, there are many workspaces, let's provide a pre-filter for it.
            let captions: QuickPickItemWithAction[] = new Array();
            for (let i = 0; i < workspaceInfo.length; i++) {
                const wsInfo: WorkspaceInfo = workspaceInfo[i];
                let caption: QuickPickItemWithAction = {
                    'label': '$(folder) ' + wsInfo.workspaceName,
                    'action': { 'filterWorkspaceId': wsInfo.workspaceId },
                };
                captions.push(caption);
            }

            sortCaptions(captions);

            let caption: QuickPickItemWithAction = {
                'label': '$(refresh) * Refresh list',
                'description': 'Expected Workspace is not appearing.',
                'sortKey': '09999', // last item
                'action': { 'refresh': true }
            };
            captions.push(caption);

            let selectedItem: QuickPickItemWithAction = await window.showQuickPick(
                captions,
                {
                    "canPickMany": false,
                    'placeHolder': 'Please select Workspace to upload: ' + robot.name + ' (' + robot.directory + ')' + '.',
                    'ignoreFocusOut': true,
                }
            );
            if (!selectedItem) {
                return;
            }
            if (selectedItem.action.refresh) {
                refresh = true;
                continue SELECT_OR_REFRESH;
            } else {
                workspaceIdFilter = selectedItem.action.filterWorkspaceId;
            }
        }

        // -------------------------------------------------------
        // Select Robot/New Robot/Refresh
        // -------------------------------------------------------

        let captions: QuickPickItemWithAction[] = new Array();
        for (let i = 0; i < workspaceInfo.length; i++) {
            const wsInfo: WorkspaceInfo = workspaceInfo[i];

            if (workspaceIdFilter) {
                if (workspaceIdFilter != wsInfo.workspaceId) {
                    continue;
                }
            }

            for (let j = 0; j < wsInfo.packages.length; j++) {
                const robotInfo = wsInfo.packages[j];

                // i.e.: Show the Robots with the same name with more priority in the list.
                let sortKey = 'b' + robotInfo.name;
                if (robotInfo.name == robot.name) {
                    sortKey = 'a' + robotInfo.name;
                }
                let caption: QuickPickItemWithAction = {
                    'label': '$(file) ' + robotInfo.name,
                    'description': '(Workspace: ' + wsInfo.workspaceName + ')',
                    'sortKey': sortKey,
                    'action': { 'existingRobotPackage': robotInfo }
                };
                captions.push(caption);
            }

            let caption: QuickPickItemWithAction = {
                'label': '$(new-folder) + Create new Robot',
                'description': '(Workspace: ' + wsInfo.workspaceName + ')',
                'sortKey': 'c' + wsInfo.workspaceName, // right before last item.
                'action': { 'newRobotPackageAtWorkspace': wsInfo }
            };
            captions.push(caption);
        }
        let caption: QuickPickItemWithAction = {
            'label': '$(refresh) * Refresh list',
            'description': 'Expected Workspace or Robot is not appearing.',
            'sortKey': 'd', // last item
            'action': { 'refresh': true }
        };
        captions.push(caption);

        sortCaptions(captions);

        let selectedItem: QuickPickItemWithAction = await window.showQuickPick(
            captions,
            {
                "canPickMany": false,
                'placeHolder': 'Please select target Robot to upload: ' + robot.name + ' (' + robot.directory + ').',
                'ignoreFocusOut': true,
            }
        );
        if (!selectedItem) {
            return;
        }
        let action = selectedItem.action;
        if (action.refresh) {
            refresh = true;
            continue SELECT_OR_REFRESH;
        }

        if (action.newRobotPackageAtWorkspace) {
            // No confirmation in this case
            let wsInfo: WorkspaceInfo = action.newRobotPackageAtWorkspace;
            await askAndCreateNewRobotAtWorkspace(wsInfo, robot.directory);
            return;
        }

        if (action.existingRobotPackage) {
            let yesOverride: string = 'Yes (override existing Robot)';
            let noChooseDifferentTarget: string = 'No (choose different target)';
            let cancel: string = 'Cancel';
            let robotInfo: PackageInfo = action.existingRobotPackage;

            let selectedItem = await window.showWarningMessage(
                "Upload of the contents of " + robot.directory + " to: " + robotInfo.name + " (" + robotInfo.workspaceName + ")", ...[yesOverride, noChooseDifferentTarget, cancel]);

            // robot.language-server.python
            if (selectedItem == noChooseDifferentTarget) {
                refresh = false;
                continue SELECT_OR_REFRESH;
            }
            if (selectedItem == cancel) {
                return;
            }
            // selectedItem == yesOverride.
            let actionResult: ActionResult = await commands.executeCommand(
                roboCommands.ROBOCORP_UPLOAD_TO_EXISTING_ROBOT_INTERNAL,
                { 'workspaceId': robotInfo.workspaceId, 'robotId': robotInfo.id, 'directory': robot.directory }
            );

            if (!actionResult.success) {
                let msg: string = 'Error uploading to existing Robot: ' + actionResult.message;
                OUTPUT_CHANNEL.appendLine(msg);
                window.showErrorMessage(msg);
            } else {
                window.showInformationMessage('Successfully submitted Robot ' + robot.name + ' to the cloud.')
            }
            return;
        }

    } while (true);
}

export async function askAndRunRobotRCC(noDebug: boolean) {
    let textEditor = window.activeTextEditor;
    let fileName: string | undefined = undefined;

    if (textEditor) {
        fileName = textEditor.document.fileName;
    }

    const RUN_IN_RCC_LRU_CACHE_NAME = 'RUN_IN_RCC_LRU_CACHE';
    let runLRU: string[] = await commands.executeCommand(roboCommands.ROBOCORP_LOAD_FROM_DISK_LRU, { 'name': RUN_IN_RCC_LRU_CACHE_NAME });

    let actionResult: ActionResult = await commands.executeCommand(roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL);
    if (!actionResult.success) {
        window.showErrorMessage('Error listing Robots: ' + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage('Unable to run Robot (no Robot detected in the Workspace).');
        return;
    }

    let items: QuickPickItemRobotTask[] = new Array();

    for (let robotInfo of robotsInfo) {
        let yamlContents = robotInfo.yamlContents
        let tasks = yamlContents['tasks'];
        if (tasks) {
            let taskNames: string[] = Object.keys(tasks);
            for (let taskName of taskNames) {
                let keyInLRU: string = robotInfo.name + ' - ' + taskName + ' - ' + robotInfo.filePath;
                let item: QuickPickItemRobotTask = {
                    'label': 'Run robot: ' + robotInfo.name + '    Task: ' + taskName,
                    'description': robotInfo.filePath,
                    'robotYaml': robotInfo.filePath,
                    'taskName': taskName,
                    'keyInLRU': keyInLRU,
                };
                if (runLRU && runLRU.length > 0 && keyInLRU == runLRU[0]) {
                    // Note that although we have an LRU we just consider the last one for now.
                    items.splice(0, 0, item);
                } else {
                    items.push(item);
                }
            }
        }
    }

    if (!items) {
        window.showInformationMessage('Unable to run Robot (no Robot detected in the Workspace).');
        return;
    }

    let selectedItem: QuickPickItemRobotTask;
    if (items.length == 1) {
        selectedItem = items[0];
    } else {
        selectedItem = await window.showQuickPick(
            items,
            {
                "canPickMany": false,
                'placeHolder': 'Please select the Robot and Task to run.',
                'ignoreFocusOut': true,
            }
        );
    }

    if (!selectedItem) {
        return;
    }

    await commands.executeCommand(
        roboCommands.ROBOCORP_SAVE_IN_DISK_LRU,
        { 'name': RUN_IN_RCC_LRU_CACHE_NAME, 'entry': selectedItem.keyInLRU, 'lru_size': 3 }
    );

    runRobotRCC(noDebug, selectedItem.robotYaml, selectedItem.taskName);
}

export async function runRobotRCC(noDebug: boolean, robotYaml: string, taskName: string) {
    let debugConfiguration: DebugConfiguration = {
        'name': 'Config',
        'type': 'robocorp-code',
        'request': 'launch',
        'robot': robotYaml,
        'task': taskName,
        'args': [],
        'noDebug': noDebug,
    };
    let debugSessionOptions: DebugSessionOptions = {};
    debug.startDebugging(undefined, debugConfiguration, debugSessionOptions)
}

export async function createRobot() {
    // Unfortunately vscode does not have a good way to request multiple inputs at once,
    // so, for now we're asking each at a separate step.
    let actionResult: ActionResult = await commands.executeCommand(roboCommands.ROBOCORP_LIST_ROBOT_TEMPLATES_INTERNAL);
    if (!actionResult.success) {
        window.showErrorMessage('Unable to list Robot templates: ' + actionResult.message);
        return;
    }
    let availableTemplates: string[] = actionResult.result;
    if (availableTemplates) {
        let wsFolders: ReadonlyArray<WorkspaceFolder> = workspace.workspaceFolders;
        if (!wsFolders) {
            window.showErrorMessage('Unable to create Robot (no workspace folder is currently opened).');
            return;
        }

        let selectedItem = await window.showQuickPick(
            availableTemplates,
            {
                "canPickMany": false,
                'placeHolder': 'Please select the template for the Robot.',
                'ignoreFocusOut': true,
            }
        );

        OUTPUT_CHANNEL.appendLine('Selected: ' + selectedItem);
        let ws: WorkspaceFolder;
        if (!selectedItem) {
            // Operation cancelled.
            return;
        }
        if (wsFolders.length == 1) {
            ws = wsFolders[0];
        } else {
            ws = await window.showWorkspaceFolderPick({
                'placeHolder': 'Please select the folder to create the Robot.',
                'ignoreFocusOut': true,
            });
        }
        if (!ws) {
            // Operation cancelled.
            return;
        }

        let name: string = await window.showInputBox({
            'value': 'Example',
            'prompt': 'Please provide the name for the Robot folder name.',
            'ignoreFocusOut': true,
        })
        if (!name) {
            // Operation cancelled.
            return;
        }

        OUTPUT_CHANNEL.appendLine('Creating Robot at: ' + ws.uri.fsPath);
        let createRobotResult: ActionResult = await commands.executeCommand(
            roboCommands.ROBOCORP_CREATE_ROBOT_INTERNAL,
            { 'directory': ws.uri.fsPath, 'template': selectedItem, 'name': name }
        );

        if (createRobotResult.success) {
            try {
                commands.executeCommand('workbench.files.action.refreshFilesExplorer');
            } catch (error) {
                OUTPUT_CHANNEL.appendLine('Error refreshing file explorer.');
            }
            window.showInformationMessage('Robot successfully created in:\n' + join(ws.uri.fsPath, name));
        } else {
            OUTPUT_CHANNEL.appendLine('Error creating Robot at: ' + + ws.uri.fsPath);
            window.showErrorMessage(createRobotResult.message);
        }
    }
}
