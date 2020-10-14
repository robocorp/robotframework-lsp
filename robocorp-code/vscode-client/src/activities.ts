import { commands, window, WorkspaceFolder, workspace, Uri, QuickPickItem, TextEdit } from "vscode";
import { join } from 'path';
import { OUTPUT_CHANNEL } from './channel';
import * as roboCommands from './robocorpCommands';

interface LocalRobotMetadataInfo {
    name: string;
    directory: string;
    filePath: string;
    yamlContents: object;
};

interface WorkspaceInfo {
    workspaceName: string;
    workspaceId: string;
    packages: PackageInfo[];
};

interface PackageInfo {
    workspaceId: string;
    workspaceName: string;
    id: string;
    name: string;
    sortKey: string;
};

interface ActionResult {
    success: boolean;
    message: string;
    result: any;
};

interface ListWorkspacesActionResult {
    success: boolean;
    message: string;
    result: WorkspaceInfo[];
};

interface QuickPickItemWithAction extends QuickPickItem {
    action: any;
    sortKey?: string;
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
            'prompt': 'Please provide the access credentials from: https://cloud.robocorp.com/settings/access-credentials',
            'ignoreFocusOut': true,
        });
        if (!credentials) {
            return false;
        }
        loggedIn = await commands.executeCommand(
            roboCommands.ROBOCORP_CLOUD_LOGIN_INTERNAL, { 'credentials': credentials }
        );
        if (!loggedIn) {
            let retry = "Retry with new credentials";
            let selection = await window.showWarningMessage('Unable to log in with the provided credentials.', { 'modal': true }, retry);
            if (!selection) {
                return false;
            }
        }
    } while (!loggedIn);
    return true;
}

async function askRobotToUpload(robotsInfo: LocalRobotMetadataInfo[]): Promise<LocalRobotMetadataInfo> {
    let robotToUpload: LocalRobotMetadataInfo;
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
        let selection: QuickPickItemWithAction = await window.showQuickPick(
            captions,
            {
                "canPickMany": false,
                'placeHolder': 'Please select the Robot to upload to the Cloud.',
                'ignoreFocusOut': true,
            }
        );
        if (!selection) {
            return;
        }
        robotToUpload = selection.action;
    } else {
        robotToUpload = robotsInfo[0];
    }
    return robotToUpload;
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

    let robotToUpload: LocalRobotMetadataInfo = await askRobotToUpload(robotsInfo);
    if (!robotToUpload) {
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
        // just show it all, otherwise do a pre-selection with the workspace.
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

            let selection: QuickPickItemWithAction = await window.showQuickPick(
                captions,
                {
                    "canPickMany": false,
                    'placeHolder': 'Please select Workspace to upload: ' + robotToUpload.name + ' (' + robotToUpload.directory + ')' + '.',
                    'ignoreFocusOut': true,
                }
            );
            if (!selection) {
                return;
            }
            if (selection.action.refresh) {
                refresh = true;
                continue SELECT_OR_REFRESH;
            } else {
                workspaceIdFilter = selection.action.filterWorkspaceId;
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
                if (robotInfo.name == robotToUpload.name) {
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

        let selection: QuickPickItemWithAction = await window.showQuickPick(
            captions,
            {
                "canPickMany": false,
                'placeHolder': 'Please select target Robot to upload: ' + robotToUpload.name + ' (' + robotToUpload.directory + ').',
                'ignoreFocusOut': true,
            }
        );
        if (!selection) {
            return;
        }
        let action = selection.action;
        if (action.refresh) {
            refresh = true;
            continue SELECT_OR_REFRESH;
        }

        if (action.newRobotPackageAtWorkspace) {
            // No confirmation in this case
            let wsInfo: WorkspaceInfo = action.newRobotPackageAtWorkspace;
            await askAndCreateNewRobotAtWorkspace(wsInfo, robotToUpload.directory);
            return;
        }

        if (action.existingRobotPackage) {
            let yesOverride: string = 'Yes (override existing Robot)';
            let noChooseDifferentTarget: string = 'No (choose different target)';
            let cancel: string = 'Cancel';
            let robotInfo: PackageInfo = action.existingRobotPackage;

            let selection = await window.showWarningMessage(
                "Upload of the contents of " + robotToUpload.directory + " to: " + robotInfo.name + " (" + robotInfo.workspaceName + ")", ...[yesOverride, noChooseDifferentTarget, cancel]);

            // robot.language-server.python
            if (selection == noChooseDifferentTarget) {
                refresh = false;
                continue SELECT_OR_REFRESH;
            }
            if (selection == cancel) {
                return;
            }
            // selection == yesOverride.
            let actionResult: ActionResult = await commands.executeCommand(
                roboCommands.ROBOCORP_UPLOAD_TO_EXISTING_ROBOT_INTERNAL,
                { 'workspaceId': robotInfo.workspaceId, 'robotId': robotInfo.id, 'directory': robotToUpload.directory }
            );

            if (!actionResult.success) {
                let msg: string = 'Error uploading to existing Robot: ' + actionResult.message;
                OUTPUT_CHANNEL.appendLine(msg);
                window.showErrorMessage(msg);
            } else {
                window.showInformationMessage('Successfully submitted Robot ' + robotToUpload.name + ' to the cloud.')
            }
            return;
        }

    } while (true);
}

export async function runRobotRCC() {
    let textEditor = window.activeTextEditor;
    let fileName: string | undefined = undefined;

    if (textEditor) {
        fileName = textEditor.document.fileName;
    }

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
    for (let robotInfo of robotsInfo) {
        let yamlContents = robotInfo.yamlContents
        let tasks = yamlContents['tasks'];
        if (tasks) {
            let taskNames: string[] = Object.keys(tasks);
            for (let taskName of taskNames) {
                // TODO: Show options to user and create the related launch configuration
                // and launch it.
            }
        }
    }

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

        let selection = await window.showQuickPick(
            availableTemplates,
            {
                "canPickMany": false,
                'placeHolder': 'Please select the template for the Robot.',
                'ignoreFocusOut': true,
            }
        );

        OUTPUT_CHANNEL.appendLine('Selected: ' + selection);
        let ws: WorkspaceFolder;
        if (!selection) {
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
            { 'directory': ws.uri.fsPath, 'template': selection, 'name': name }
        );

        if (createRobotResult.success) {
            window.showInformationMessage('Robot successfully created in:\n' + join(ws.uri.fsPath, name));
        } else {
            OUTPUT_CHANNEL.appendLine('Error creating Robot at: ' + + ws.uri.fsPath);
            window.showErrorMessage(createRobotResult.message);
        }
    }
}
