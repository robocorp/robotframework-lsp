import { commands, window, WorkspaceFolder, workspace, Uri } from "vscode";
import { join } from 'path';
import { OUTPUT_CHANNEL } from './channel';
import * as roboCommands from './robocodeCommands';

interface ActivityInfo {
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
    lastSelected: boolean;
};

interface ActionResult {
    success: boolean;
    message: string;
    result: any;
};



export async function uploadActivity() {
    let currentUri: Uri;
    if (window.activeTextEditor && window.activeTextEditor.document) {
        currentUri = window.activeTextEditor.document.uri;
    }
    let actionResult: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCODE_LOCAL_LIST_ACTIVITIES_INTERNAL,
        { 'currentUri': currentUri }
    );
    if (!actionResult.success) {
        window.showInformationMessage('Error submitting activity package to the cloud: ' + actionResult.message);
        return;
    }
    let activitiesInfo: ActivityInfo[] = actionResult.result;

    if (!activitiesInfo) {
        window.showInformationMessage('Unable to submit activity package to the cloud (no activity detected in the workspace).');
        return;
    }

    let isLoginNeeded: boolean = await commands.executeCommand(
        roboCommands.ROBOCODE_IS_LOGIN_NEEDED_INTERNAL,
    );

    if (isLoginNeeded) {
        let loggedIn: boolean;
        do {
            let credentials: string = await window.showInputBox({
                'password': true,
                'prompt': 'Please provide the access credentials from: https://cloud.robocorp.com/settings/access-credentials'
            });
            if (!credentials) {
                return;
            }
            loggedIn = await commands.executeCommand(
                roboCommands.ROBOCODE_CLOUD_LOGIN_INTERNAL, { 'credentials': credentials }
            );
            if (!loggedIn) {
                let retry = "Enter new credentials?";
                let selection = await window.showWarningMessage('Unable to log in with the provided credentials.', { 'modal': true }, retry);
                if (!selection) {
                    return;
                }
            }
        } while (!loggedIn);
    }

    let activityToUpload: ActivityInfo;
    if (activitiesInfo.length > 1) {
        let captionToActivity: Map<string, ActivityInfo> = new Map();
        let captions: string[] = new Array();

        for (let i = 0; i < activitiesInfo.length; i++) {
            const element: ActivityInfo = activitiesInfo[i];
            let caption = element.name + '\t(' + element.directory + ')';
            captions.push(caption);
            captionToActivity[caption] = element;
        }
        let selection: string = await window.showQuickPick(
            captions,
            { "canPickMany": false, 'placeHolder': 'Please select the activity package to upload to the cloud.' }
        );
        if (!selection) {
            return;
        }
        activityToUpload = captionToActivity[selection];
    } else {
        activityToUpload = activitiesInfo[0];
    }

    let refresh = false;
    do {
        // We ask for the information on the existing workspaces information.
        // Note that this may be cached from the last time it was asked, 
        // so, we have an option to refresh it (and ask again).
        let actionResult: ActionResult = await commands.executeCommand(
            roboCommands.ROBOCODE_CLOUD_LIST_WORKSPACES_INTERNAL, { 'refresh': refresh, 'packages': true }
        );

        if (!actionResult.success) {
            window.showErrorMessage('Error listing cloud workspaces: ' + actionResult.message);
            return;
        }

        let workspaceInfo: WorkspaceInfo[] = actionResult.result;

        let captionToAction: Map<string, Object> = new Map();

        let captions: string[] = new Array();
        for (let i = 0; i < workspaceInfo.length; i++) {
            const wsInfo: WorkspaceInfo = workspaceInfo[i];
            for (let j = 0; j < wsInfo.packages.length; j++) {
                const packageInfo = wsInfo.packages[j];
                let caption = packageInfo.name + '\t(Workspace: ' + wsInfo.workspaceName + ')';
                if (packageInfo.lastSelected) {
                    captions.splice(0, 0, caption);
                } else {
                    captions.push(caption);
                }
                captionToAction[caption] = { 'existingActivityPackage': packageInfo };
            }

            // TODO: Submit to new activity
            // let caption: string = 'New activity package at workspace: ' + wsInfo.workspaceName;
            // captions.push(caption);
            // captionToAction[caption] = { 'newActivityPackageAtWorkspace': wsInfo };
        }
        let caption: string = 'Refresh list (expected workspace or package is not appearing)';
        captions.push(caption);
        captionToAction[caption] = { 'refresh': true };

        let selection: string = await window.showQuickPick(
            captions,
            { "canPickMany": false, 'placeHolder': 'Please select the activity package to upload to the cloud.' }
        );
        if (!selection) {
            return;
        }
        let action = captionToAction[selection];
        if (action.refresh) {
            refresh = true;
            continue;
        }
        // TODO: Submit to new activity
        // if (action.newActivityPackageAtWorkspace) {
        //     await commands.executeCommand(
        //         roboCommands.ROBOCODE_UPLOAD_TO_NEW_ACTIVITY_INTERNAL, { 'workspace': refresh }
        //     );
        // }
        if (action.existingActivityPackage) {
            let packageInfo: PackageInfo = action.existingActivityPackage;
            let actionResult: ActionResult = await commands.executeCommand(
                roboCommands.ROBOCODE_UPLOAD_TO_EXISTING_ACTIVITY_INTERNAL,
                { 'workspaceId': packageInfo.workspaceId, 'packageId': packageInfo.id, 'directory': activityToUpload.directory }
            );

            if (!actionResult.success) {
                window.showErrorMessage('Error uploading to existing activity package: ' + actionResult.message);
            }
            return;
        }

    } while (true);


}

export async function createActivity() {
    // Unfortunately vscode does not have a good way to request multiple inputs at once,
    // so, for now we're asking each at a separate step.
    let actionResult: ActionResult = await commands.executeCommand(roboCommands.ROBOCODE_LIST_ACTIVITY_TEMPLATES_INTERNAL);
    if (!actionResult.success) {
        window.showErrorMessage('Unable to list activity templates: ' + actionResult.message);
        return;
    }
    let availableTemplates: string[] = actionResult.result;
    if (availableTemplates) {
        let wsFolders: ReadonlyArray<WorkspaceFolder> = workspace.workspaceFolders;
        if (!wsFolders) {
            window.showErrorMessage('Unable to create Activity Package (no workspace folder is currently opened).');
            return;
        }

        let selection = await window.showQuickPick(
            availableTemplates,
            { "canPickMany": false, 'placeHolder': 'Please select the template for the activity package.' }
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
            ws = await window.showWorkspaceFolderPick({ 'placeHolder': 'Please select the folder to create the activity package.' });
        }
        if (!ws) {
            // Operation cancelled.
            return;
        }

        let name: string = await window.showInputBox({ 'value': 'Example', 'prompt': 'Please provide the name for the activity folder name.' })
        if (!name) {
            // Operation cancelled.
            return;
        }

        OUTPUT_CHANNEL.appendLine('Creating activity at: ' + ws.uri.fsPath);
        let createActivityResult: ActionResult = await commands.executeCommand(
            roboCommands.ROBOCODE_CREATE_ACTIVITY_INTERNAL,
            { 'directory': ws.uri.fsPath, 'template': selection, 'name': name }
        );

        if (createActivityResult.success) {
            window.showInformationMessage('Activity package successfuly created in:\n' + join(ws.uri.fsPath, name));
        } else {
            OUTPUT_CHANNEL.appendLine('Error creating activity at: ' + + ws.uri.fsPath);
            window.showErrorMessage(createActivityResult.message);
        }
    }
}
