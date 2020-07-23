import { commands, window, WorkspaceFolder, workspace } from "vscode";
import { join } from 'path';
import { OUTPUT_CHANNEL } from './channel';
import * as roboCommands from './robocodeCommands';

export async function createActivity() {
    // Unfortunately vscode does not have a good way to request multiple inputs at once,
    // so, for now we're asking each at a separate step.
    let availableTemplates: string[] = await commands.executeCommand(roboCommands.ROBOCODE_LIST_ACTIVITY_TEMPLATES_INTERNAL);
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

        let name: string = await window.showInputBox({ 'value': 'Example1', 'prompt': 'Please provide the name for the activity folder name.' })
        if (!name) {
            // Operation cancelled.
            return;
        }

        OUTPUT_CHANNEL.appendLine('Creating activity at: ' + ws.uri.fsPath);
        let result = await commands.executeCommand(
            roboCommands.ROBOCODE_CREATE_ACTIVITY_INTERNAL,
            { 'directory': ws.uri.fsPath, 'template': selection, 'name': name }
        );

        if (result['result'] == 'ok') {
            window.showInformationMessage('Activity package successfuly created in:\n' + join(ws.uri.fsPath, name));
        } else {
            OUTPUT_CHANNEL.appendLine('Result: ' + result['result'] + '\nMessage: ' + result['message']);
            window.showErrorMessage(result['message']);
        }
    }
}
