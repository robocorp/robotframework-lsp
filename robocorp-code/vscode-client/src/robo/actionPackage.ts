import { QuickPickItem, commands, window } from "vscode";
import * as vscode from "vscode";
import * as roboCommands from "../robocorpCommands";
import { ActionResult, IActionInfo, LocalRobotMetadataInfo } from "../protocols";
import { isActionPackage } from "../common";
import { slugify } from "../slugify";
import { fileExists, makeDirs } from "../files";
import { QuickPickItemWithAction, showSelectOneQuickPick } from "../ask";
import * as path from "path";
import { logError } from "../channel";

export interface QuickPickItemAction extends QuickPickItem {
    actionPackageUri: vscode.Uri;
    actionFileUri: vscode.Uri;
    actionPackageYamlDirectory: string;
    packageYaml: string;
    actionName: string;
    keyInLRU: string;
}

export async function createDefaultInputJson(inputUri: vscode.Uri) {
    await vscode.workspace.fs.writeFile(
        inputUri,
        Buffer.from(`{
    "paramName": "paramValue"
}`)
    );
}

export async function askAndRunRobocorpActionFromActionPackage(noDebug: boolean) {
    let textEditor = window.activeTextEditor;
    let fileName: string | undefined = undefined;

    if (textEditor) {
        fileName = textEditor.document.fileName;
    }

    const RUN_ACTION_FROM_ACTION_PACKAGE_LRU_CACHE = "RUN_ACTION_FROM_ACTION_PACKAGE_LRU_CACHE";
    let runLRU: string[] = await commands.executeCommand(roboCommands.ROBOCORP_LOAD_FROM_DISK_LRU, {
        "name": RUN_ACTION_FROM_ACTION_PACKAGE_LRU_CACHE,
    });

    let actionResult: ActionResult<LocalRobotMetadataInfo[]> = await commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );
    if (!actionResult.success) {
        window.showErrorMessage("Error listing Action Packages: " + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;
    if (robotsInfo) {
        // Only use action packages.
        robotsInfo = robotsInfo.filter((r) => {
            return isActionPackage(r);
        });
    }

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage("Unable to run Action Package (no Action Packages detected in the Workspace).");
        return;
    }

    let items: QuickPickItemAction[] = new Array();

    for (let robotInfo of robotsInfo) {
        try {
            const actionPackageUri = vscode.Uri.file(robotInfo.filePath);
            let result: ActionResult<undefined> = await vscode.commands.executeCommand(
                roboCommands.ROBOCORP_LIST_ACTIONS_INTERNAL,
                {
                    "action_package": actionPackageUri.toString(),
                }
            );
            if (result.success) {
                let actions: IActionInfo[] = result.result;
                for (const action of actions) {
                    const keyInLRU = `${robotInfo.name}: ${action.name}`;
                    const uri = vscode.Uri.parse(action.uri);
                    const item: QuickPickItemAction = {
                        "label": keyInLRU,
                        "actionName": action.name,
                        "actionFileUri": uri,
                        "actionPackageYamlDirectory": robotInfo.directory,
                        "actionPackageUri": actionPackageUri,
                        "packageYaml": robotInfo.filePath,
                        "keyInLRU": action.name,
                    };
                    if (runLRU && runLRU.length > 0 && keyInLRU == runLRU[0]) {
                        // Note that although we have an LRU we just consider the last one for now.
                        items.splice(0, 0, item);
                    } else {
                        items.push(item);
                    }
                }
            }
        } catch (error) {
            logError("Error collecting actions.", error, "ACT_COLLECT_ACTIONS");
        }
    }

    if (!items) {
        window.showInformationMessage("Unable to run Action Package (no Action Package detected in the Workspace).");
        return;
    }

    let selectedItem: QuickPickItemAction;
    if (items.length == 1) {
        selectedItem = items[0];
    } else {
        selectedItem = await window.showQuickPick(items, {
            "canPickMany": false,
            "placeHolder": "Please select the Action Package and Action to run.",
            "ignoreFocusOut": true,
        });
    }

    if (!selectedItem) {
        return;
    }

    await commands.executeCommand(roboCommands.ROBOCORP_SAVE_IN_DISK_LRU, {
        "name": RUN_ACTION_FROM_ACTION_PACKAGE_LRU_CACHE,
        "entry": selectedItem.keyInLRU,
        "lru_size": 3,
    });

    const actionName: string = selectedItem.actionName;
    const actionPackageYamlDirectory: string = selectedItem.actionPackageYamlDirectory;
    const packageYaml: string = selectedItem.actionPackageUri.fsPath;
    const actionFileUri: vscode.Uri = selectedItem.actionFileUri;
    await runActionFromActionPackage(noDebug, actionName, actionPackageYamlDirectory, packageYaml, actionFileUri);
}

export async function getTargetInputJson(actionName: string, actionPackageYamlDirectory: string): Promise<string> {
    const nameSlugified = slugify(actionName);

    const dir = actionPackageYamlDirectory;
    const devDataDir = path.join(dir, "devdata");
    await makeDirs(devDataDir);
    const targetInput = path.join(devDataDir, `input_${nameSlugified}.json`);
    return targetInput;
}

export async function runActionFromActionPackage(
    noDebug: boolean,
    actionName: string,
    actionPackageYamlDirectory: string,
    packageYaml: string,
    actionFileUri: vscode.Uri
) {
    // The input must be asked when running actions in this case and it should be
    // saved in 'devdata/input_xxx.json'
    const nameSlugified = slugify(actionName);
    const targetInput = await getTargetInputJson(actionName, actionPackageYamlDirectory);

    if (!(await fileExists(targetInput))) {
        let items: QuickPickItemWithAction[] = new Array();

        items.push({
            "label": `Create "devdata/input_${nameSlugified}.json" to customize action input`,
            "action": "create",
            "detail": "Note: Please relaunch after the customization is completed",
        });

        items.push({
            "label": `Cancel`,
            "action": "cancel",
        });

        let selectedItem: QuickPickItemWithAction | undefined = await showSelectOneQuickPick(
            items,
            "Input for the action not defined. How to proceed?",
            `Customize input for the ${actionName} action`
        );
        if (!selectedItem) {
            return;
        }

        if (selectedItem.action === "create") {
            // Create the file and ask the user to fill it and rerun the action
            // after he finished doing that.
            const inputUri = vscode.Uri.file(targetInput);
            await createDefaultInputJson(inputUri);
            await vscode.window.showTextDocument(inputUri);
        }
        // In any case, don't proceed if it wasn't previously created
        // (so that the user can customize it).
        return;
    }

    // Ok, input available. Let's create the launch and run it.
    let debugConfiguration: vscode.DebugConfiguration = {
        "name": "Config",
        "type": "robocorp-code",
        "request": "launch",
        "package": packageYaml,
        "uri": actionFileUri.toString(),
        "jsonInput": targetInput,
        "actionName": actionName,
        "args": [],
        "noDebug": noDebug,
    };
    let debugSessionOptions: vscode.DebugSessionOptions = {};
    vscode.debug.startDebugging(undefined, debugConfiguration, debugSessionOptions);
}
