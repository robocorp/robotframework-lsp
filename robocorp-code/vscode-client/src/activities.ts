import { commands, window, WorkspaceFolder, workspace, Uri, QuickPickItem } from "vscode";
import { join } from 'path';
import { OUTPUT_CHANNEL } from './channel';
import * as roboCommands from './robocorpCommands';

interface RobotInfo {
    name: string;
    directory: string;
};

interface WorkspaceInfo {
    workspaceName: string;
    workspaceId: string;
    packages: PackageInfo[];
};

interface PackageInfo {
    workspaceId: string;
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


export async function cloudLogin() : Promise<boolean> {
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
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL,
        { 'currentUri': currentUri }
    );
    if (!actionResult.success) {
        window.showInformationMessage('Error submitting robot to the cloud: ' + actionResult.message);
        return;
    }
    let activitiesInfo: RobotInfo[] = actionResult.result;

    if (!activitiesInfo || activitiesInfo.length == 0) {
        window.showInformationMessage('Unable to submit robot to the cloud (no robot detected in the workspace).');
        return;
    }

    let isLoginNeeded: ActionResult = await isLoginNeededPromise;
    if (!isLoginNeeded) {
        window.showInformationMessage('Error getting if login is needed.');
        return;
    }

    if (isLoginNeeded.result) {
        let loggedIn: boolean = await cloudLogin();
        if(!loggedIn){
            return;
        }
    }

    let activityToUpload: RobotInfo;
    if (activitiesInfo.length > 1) {
        let captionToRobot: Map<string, RobotInfo> = new Map();
        let captions: QuickPickItemWithAction[] = new Array();

        for (let i = 0; i < activitiesInfo.length; i++) {
            const element: RobotInfo = activitiesInfo[i];
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
                'placeHolder': 'Please select the robot to upload to the cloud.',
                'ignoreFocusOut': true,
            }
        );
        if (!selection) {
            return;
        }
        activityToUpload = selection.action;
    } else {
        activityToUpload = activitiesInfo[0];
    }

    let refresh = false;
    do {
        // We ask for the information on the existing workspaces information.
        // Note that this may be cached from the last time it was asked, 
        // so, we have an option to refresh it (and ask again).
        let actionResult: ListWorkspacesActionResult = await commands.executeCommand(
            roboCommands.ROBOCORP_CLOUD_LIST_WORKSPACES_INTERNAL, { 'refresh': refresh, 'packages': true }
        );

        if (!actionResult.success) {
            window.showErrorMessage('Error listing cloud workspaces: ' + actionResult.message);
            return;
        }

        let workspaceInfo: WorkspaceInfo[] = actionResult.result;
        if (!workspaceInfo || workspaceInfo.length == 0) {
            window.showErrorMessage('A cloud workspace must be created to submit a robot to the cloud.');
            return;
        }

        // --------------------------------------------------------
        // Select robot/new package/refresh
        // -------------------------------------------------------

        let captions: QuickPickItemWithAction[] = new Array();
        for (let i = 0; i < workspaceInfo.length; i++) {
            const wsInfo: WorkspaceInfo = workspaceInfo[i];
            for (let j = 0; j < wsInfo.packages.length; j++) {
                const robotInfo = wsInfo.packages[j];
                let caption: QuickPickItemWithAction = {
                    'label': '$(file) ' + robotInfo.name,
                    'description': '(Workspace: ' + wsInfo.workspaceName + ')',
                    'sortKey': robotInfo.sortKey,
                    'action': { 'existingRobotPackage': robotInfo }    
                };
                captions.push(caption);
            }

            let caption: QuickPickItemWithAction = {
                'label': '$(new-folder) New robot',
                'description': '(Workspace: ' + wsInfo.workspaceName + ')',
                'sortKey': '09998', // right before last item.
                'action': { 'newRobotPackageAtWorkspace': wsInfo }
            };
            captions.push(caption);
        }
        let caption: QuickPickItemWithAction = {
            'label': '$(refresh) Refresh list',
            'description': 'Expected workspace or package is not appearing.',
            'sortKey': '09999', // last item
            'action': { 'refresh': true }
        };
        captions.push(caption);

        captions.sort(function (a, b) {
            if (a.sortKey < b.sortKey) {
                return -1;
            }
            if (a.sortKey > b.sortKey) {
                return 1;
            }

            if(a.label < b.label){
                return -1;
            }
            if(a.label > b.label){
                return 1;
            }

            return 0;
        });

        let selection: QuickPickItemWithAction = await window.showQuickPick(
            captions,
            {
                "canPickMany": false,
                'placeHolder': 'Please select target robot to upload: ' + activityToUpload.name + ' (' + activityToUpload.directory + ').',
                'ignoreFocusOut': true,
            }
        );
        if (!selection) {
            return;
        }
        let action = selection.action;
        if (action.refresh) {
            refresh = true;

        } else if (action.newRobotPackageAtWorkspace) {
            let wsInfo: WorkspaceInfo = action.newRobotPackageAtWorkspace;

            let packageName: string = await window.showInputBox({
                'prompt': 'Please provide the name for the new package.',
                'ignoreFocusOut': true,
            });
            if (!packageName) {
                return;
            }

            let actionResult: ActionResult = await commands.executeCommand(
                roboCommands.ROBOCORP_UPLOAD_TO_NEW_ROBOT_INTERNAL,
                { 'workspaceId': wsInfo.workspaceId, 'directory': activityToUpload.directory, 'packageName': packageName }
            );
            if (!actionResult.success) {
                let msg:string = 'Error uploading to new robot: ' + actionResult.message;
                OUTPUT_CHANNEL.appendLine(msg);
                window.showErrorMessage(msg);
            }else{
                window.showInformationMessage('Successfully submited robot to the cloud.')
            }
            return;

        } else if (action.existingRobotPackage) {
            let robotInfo: PackageInfo = action.existingRobotPackage;
            let actionResult: ActionResult = await commands.executeCommand(
                roboCommands.ROBOCORP_UPLOAD_TO_EXISTING_ROBOT_INTERNAL,
                { 'workspaceId': robotInfo.workspaceId, 'robotId': robotInfo.id, 'directory': activityToUpload.directory }
            );

            if (!actionResult.success) {
                let msg: string = 'Error uploading to existing robot: ' + actionResult.message;
                OUTPUT_CHANNEL.appendLine(msg);
                window.showErrorMessage(msg);
            }else{
                window.showInformationMessage('Successfully submited robot to the cloud.')
            }
            return;
        }

    } while (true);


}

export async function createRobot() {
    // Unfortunately vscode does not have a good way to request multiple inputs at once,
    // so, for now we're asking each at a separate step.
    let actionResult: ActionResult = await commands.executeCommand(roboCommands.ROBOCORP_LIST_ROBOT_TEMPLATES_INTERNAL);
    if (!actionResult.success) {
        window.showErrorMessage('Unable to list robot templates: ' + actionResult.message);
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
                'placeHolder': 'Please select the template for the robot.',
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
                'placeHolder': 'Please select the folder to create the robot.',
                'ignoreFocusOut': true,
            });
        }
        if (!ws) {
            // Operation cancelled.
            return;
        }

        let name: string = await window.showInputBox({
            'value': 'Example',
            'prompt': 'Please provide the name for the robot folder name.',
            'ignoreFocusOut': true,
        })
        if (!name) {
            // Operation cancelled.
            return;
        }

        OUTPUT_CHANNEL.appendLine('Creating robot at: ' + ws.uri.fsPath);
        let createRobotResult: ActionResult = await commands.executeCommand(
            roboCommands.ROBOCORP_CREATE_ROBOT_INTERNAL,
            { 'directory': ws.uri.fsPath, 'template': selection, 'name': name }
        );

        if (createRobotResult.success) {
            window.showInformationMessage('Robot successfully created in:\n' + join(ws.uri.fsPath, name));
        } else {
            OUTPUT_CHANNEL.appendLine('Error creating robot at: ' + + ws.uri.fsPath);
            window.showErrorMessage(createRobotResult.message);
        }
    }
}
