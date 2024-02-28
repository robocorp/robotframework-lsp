import { QuickPickItem, WorkspaceFolder, commands, window } from "vscode";
import * as vscode from "vscode";
import { join, dirname } from "path";
import * as roboCommands from "../robocorpCommands";
import { ActionResult, IActionInfo, LocalRobotMetadataInfo } from "../protocols";
import {
    areThereRobotsInWorkspace,
    isActionPackage,
    isDirectoryAPackageDirectory,
    verifyIfPathOkToCreatePackage,
} from "../common";
import { slugify } from "../slugify";
import { fileExists, makeDirs } from "../files";
import { QuickPickItemWithAction, askForWs, showSelectOneQuickPick } from "../ask";
import * as path from "path";
import { OUTPUT_CHANNEL, logError } from "../channel";
import { downloadOrGetActionServerLocation } from "../actionServer";
import { createEnvWithRobocorpHome, getRobocorpHome } from "../rcc";
import { execFilePromise } from "../subprocess";

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

export async function createActionPackage() {
    const robotsInWorkspacePromise: Promise<boolean> = areThereRobotsInWorkspace();
    const actionServerLocation = await downloadOrGetActionServerLocation();
    if (!actionServerLocation) {
        return;
    }

    let ws: WorkspaceFolder | undefined = await askForWs();
    if (!ws) {
        // Operation cancelled.
        return;
    }

    if (await isDirectoryAPackageDirectory(ws.uri)) {
        return;
    }

    const robotsInWorkspace: boolean = await robotsInWorkspacePromise;
    let useWorkspaceFolder: boolean;
    if (robotsInWorkspace) {
        // i.e.: if we already have robots, this is a multi-Robot workspace.
        useWorkspaceFolder = false;
    } else {
        const USE_WORKSPACE_FOLDER_LABEL = "Use workspace folder (recommended)";
        let target = await window.showQuickPick(
            [
                {
                    "label": USE_WORKSPACE_FOLDER_LABEL,
                    "detail": "The workspace will only have a single Action Package.",
                },
                {
                    "label": "Use child folder in workspace (advanced)",
                    "detail": "Multiple Action Packages can be created in this workspace.",
                },
            ],
            {
                "placeHolder": "Where do you want to create the Action Package?",
                "ignoreFocusOut": true,
            }
        );

        if (!target) {
            // Operation cancelled.
            return;
        }
        useWorkspaceFolder = target["label"] == USE_WORKSPACE_FOLDER_LABEL;
    }

    let targetDir = ws.uri.fsPath;
    if (!useWorkspaceFolder) {
        let name: string = await window.showInputBox({
            "value": "Example",
            "prompt": "Please provide the name for the Action Package folder name.",
            "ignoreFocusOut": true,
        });
        if (!name) {
            // Operation cancelled.
            return;
        }
        targetDir = join(targetDir, name);
    }

    // Now, let's validate if we can indeed create an Action Package in the given folder.
    const op = await verifyIfPathOkToCreatePackage(targetDir);
    let force: boolean;
    switch (op) {
        case "force":
            force = true;
            break;
        case "empty":
            force = false;
            break;
        case "cancel":
            return;
        default:
            throw Error("Unexpected result: " + op);
    }

    const robocorpHome = await getRobocorpHome();
    const env = createEnvWithRobocorpHome(robocorpHome);

    const cwd = dirname(targetDir);
    const useName = path.basename(targetDir);

    try {
        await execFilePromise(actionServerLocation, ["new", "--name", useName], { "env": env, "cwd": cwd });
        try {
            commands.executeCommand("workbench.files.action.refreshFilesExplorer");
        } catch (error) {
            logError("Error refreshing file explorer.", error, "ACT_REFRESH_FILE_EXPLORER");
        }
        window.showInformationMessage("Action Package successfully created in:\n" + targetDir);
    } catch (err) {
        const errorMsg = "Error creating Action Package at: " + targetDir;
        logError(errorMsg, err, "ERR_CREATE_ACTION_PACKAGE");
        OUTPUT_CHANNEL.appendLine(errorMsg);
        window.showErrorMessage(errorMsg + " (see `OUTPUT > Robocorp Code` for more details).");
    }
}
