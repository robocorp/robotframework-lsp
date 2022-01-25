import {
    commands,
    window,
    WorkspaceFolder,
    workspace,
    Uri,
    debug,
    DebugConfiguration,
    DebugSessionOptions,
    env,
    FileType,
} from "vscode";
import { join, dirname } from "path";
import { logError, OUTPUT_CHANNEL } from "./channel";
import * as roboCommands from "./robocorpCommands";
import * as vscode from "vscode";
import * as pythonExtIntegration from "./pythonExtIntegration";
import { QuickPickItemWithAction, sortCaptions, QuickPickItemRobotTask, showSelectOneQuickPick } from "./ask";
import { refreshCloudTreeView } from "./views";
import { feedback, feedbackRobocorpCodeError } from "./rcc";

export async function cloudLogin(): Promise<boolean> {
    let loggedIn: boolean;
    do {
        let credentials: string = await window.showInputBox({
            "password": true,
            "prompt":
                "1. Press the Enter key to open Control Room and create a new access credential. 2. Paste the access credential in the field above ",
            "ignoreFocusOut": true,
        });
        if (credentials == undefined) {
            return false;
        }
        if (!credentials) {
            env.openExternal(Uri.parse("https://cloud.robocorp.com/settings/access-credentials"));
            continue;
        }
        let commandResult: ActionResult<any> = await commands.executeCommand(
            roboCommands.ROBOCORP_CLOUD_LOGIN_INTERNAL,
            {
                "credentials": credentials,
            }
        );
        if (!commandResult) {
            loggedIn = false;
        } else {
            loggedIn = commandResult.success;
        }
        if (!loggedIn) {
            let retry = "Retry with new credentials";
            let selectedItem = await window.showWarningMessage(
                "Unable to log in with the provided credentials.",
                { "modal": true },
                retry
            );
            if (!selectedItem) {
                return false;
            }
        }
    } while (!loggedIn);

    return true;
}

export async function cloudLogout(): Promise<void> {
    let loggedOut: ActionResult<boolean>;

    let isLoginNeededActionResult: ActionResult<boolean> = await commands.executeCommand(
        roboCommands.ROBOCORP_IS_LOGIN_NEEDED_INTERNAL
    );
    if (!isLoginNeededActionResult) {
        window.showInformationMessage("Error getting information if already linked in.");
        return;
    }

    if (isLoginNeededActionResult.result) {
        window.showInformationMessage(
            "Unable to unlink and remove credentials from Control Room. Current Control Room credentials are not valid."
        );
        refreshCloudTreeView();
        return;
    }
    let YES = "Unlink";
    const result = await window.showWarningMessage(
        `Are you sure you want to unlink and remove credentials from Control Room?`,
        { "modal": true },
        YES
    );
    if (result !== YES) {
        return;
    }
    loggedOut = await commands.executeCommand(roboCommands.ROBOCORP_CLOUD_LOGOUT_INTERNAL);
    if (!loggedOut) {
        window.showInformationMessage("Error unlinking and removing Control Room credentials.");
        return;
    }
    if (!loggedOut.success) {
        window.showInformationMessage("Unable to unlink and remove Control Room credentials.");
        return;
    }
    window.showInformationMessage("Control Room credentials successfully unlinked and removed.");
}

/**
 * Note that callers need to check both whether it was successful as well as if the interpreter was resolved.
 */
export async function resolveInterpreter(targetRobot: string): Promise<ActionResult<InterpreterInfo | undefined>> {
    // Note: this may also activate robotframework-lsp if it's still not activated
    // (so, it cannot be used during startup as there'd be a cyclic dependency).
    try {
        let interpreter: InterpreterInfo | undefined = await commands.executeCommand(
            "robot.resolveInterpreter",
            targetRobot
        );
        return { "success": true, "message": "", "result": interpreter };
    } catch (error) {
        // We couldn't resolve with the robotframework language server command, fallback to the robocorp code command.
        try {
            let result: ActionResult<InterpreterInfo | undefined> = await commands.executeCommand(
                roboCommands.ROBOCORP_RESOLVE_INTERPRETER,
                {
                    "target_robot": targetRobot,
                }
            );
            return result;
        } catch (error) {
            logError("Error resolving interpreter.", error, "ACT_RESOLVE_INTERPRETER");
            return { "success": false, "message": "Unable to resolve interpreter.", "result": undefined };
        }
    }
}

export async function listAndAskRobotSelection(
    selectionMessage: string,
    noRobotErrorMessage: string
): Promise<LocalRobotMetadataInfo> {
    let actionResult: ActionResult<LocalRobotMetadataInfo[]> = await commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );

    if (!actionResult.success) {
        window.showInformationMessage("Error listing robots: " + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage(noRobotErrorMessage);
        return;
    }

    let robot: LocalRobotMetadataInfo = await askRobotSelection(robotsInfo, selectionMessage);
    if (!robot) {
        return;
    }
    return robot;
}

export async function askRobotSelection(
    robotsInfo: LocalRobotMetadataInfo[],
    message: string
): Promise<LocalRobotMetadataInfo> {
    let robot: LocalRobotMetadataInfo;
    if (robotsInfo.length > 1) {
        let captions: QuickPickItemWithAction[] = new Array();

        for (let i = 0; i < robotsInfo.length; i++) {
            const element: LocalRobotMetadataInfo = robotsInfo[i];
            let caption: QuickPickItemWithAction = {
                "label": element.name,
                "description": element.directory,
                "action": element,
            };
            captions.push(caption);
        }
        let selectedItem: QuickPickItemWithAction = await showSelectOneQuickPick(captions, message);
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
        "prompt": "Please provide the name for the new Robot.",
        "ignoreFocusOut": true,
    });
    if (!robotName) {
        return;
    }

    let actionResult: ActionResult<any> = await commands.executeCommand(
        roboCommands.ROBOCORP_UPLOAD_TO_NEW_ROBOT_INTERNAL,
        {
            "workspaceId": wsInfo.workspaceId,
            "directory": directory,
            "robotName": robotName,
        }
    );
    if (!actionResult.success) {
        let msg: string = "Error uploading to new Robot: " + actionResult.message;
        OUTPUT_CHANNEL.appendLine(msg);
        window.showErrorMessage(msg);
    } else {
        window.showInformationMessage("Successfully submitted new Robot " + robotName + " to the Control Room.");
    }
}

export async function setPythonInterpreterFromRobotYaml() {
    let actionResult: ActionResult<LocalRobotMetadataInfo[]> = await commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );
    if (!actionResult.success) {
        window.showInformationMessage("Error listing existing robots: " + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage(
            "Unable to set Python extension interpreter (no Robot detected in the Workspace)."
        );
        return;
    }

    let robot: LocalRobotMetadataInfo = await askRobotSelection(
        robotsInfo,
        "Please select the Robot from which the python executable should be used."
    );
    if (!robot) {
        return;
    }

    try {
        let result: ActionResult<InterpreterInfo | undefined> = await resolveInterpreter(robot.filePath);
        if (!result.success) {
            window.showWarningMessage("Error resolving interpreter info: " + result.message);
            return;
        }
        let interpreter: InterpreterInfo = result.result;
        if (!interpreter || !interpreter.pythonExe) {
            window.showWarningMessage("Unable to obtain interpreter information from: " + robot.filePath);
            return;
        }

        // Note: if we got here we have a robot in the workspace.

        await pythonExtIntegration.setPythonInterpreterForPythonExtension(
            interpreter.pythonExe,
            Uri.file(robot.filePath)
        );

        let resource = Uri.file(dirname(robot.filePath));
        let pythonExecutableConfigured = await pythonExtIntegration.getPythonExecutable(resource);
        if (pythonExecutableConfigured == "config") {
            window.showInformationMessage("Successfully set python executable path for vscode-python.");
        } else if (!pythonExecutableConfigured) {
            window.showInformationMessage(
                "Unable to verify if vscode-python executable was properly set. See OUTPUT -> Robocorp Code for more info."
            );
        } else {
            if (pythonExecutableConfigured != interpreter.pythonExe) {
                let opt1 = "Copy python path to clipboard and call vscode-python command to set interpreter";
                let opt2 = "Open more info/instructions to opt-out of the pythonDeprecadePythonPath experiment";
                let selectedItem = await window.showQuickPick([opt1, opt2, "Cancel"], {
                    "canPickMany": false,
                    "placeHolder":
                        "Unable to set the interpreter (due to pythonDeprecatePythonPath experiment). How to proceed?",
                    "ignoreFocusOut": true,
                });
                if (selectedItem == opt1) {
                    await vscode.env.clipboard.writeText(interpreter.pythonExe);
                    await commands.executeCommand("python.setInterpreter");
                } else if (selectedItem == opt2) {
                    env.openExternal(
                        Uri.parse(
                            "https://github.com/microsoft/vscode-python/wiki/AB-Experiments#pythondeprecatepythonpath"
                        )
                    );
                }
            } else {
                window.showInformationMessage("Successfully set python executable path for vscode-python.");
            }
        }
    } catch (error) {
        logError(
            "Error setting interpreter in python extension configuration.",
            error,
            "ACT_SETTING_PYTHON_PYTHONPATH"
        );
        window.showWarningMessage("Error setting interpreter in python extension configuration: " + error.message);
        return;
    }
}

export async function rccConfigurationDiagnostics() {
    let actionResult: ActionResult<LocalRobotMetadataInfo[]> = await commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );
    if (!actionResult.success) {
        window.showInformationMessage("Error listing robots: " + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage(
            "No Robot detected in the Workspace. If a robot.yaml is available, open it for more information."
        );
        return;
    }

    let robot = await askRobotSelection(robotsInfo, "Please select the Robot to analyze.");
    if (!robot) {
        return;
    }

    let diagnosticsActionResult: ActionResult<string> = await commands.executeCommand(
        roboCommands.ROBOCORP_CONFIGURATION_DIAGNOSTICS_INTERNAL,
        { "robotYaml": robot.filePath }
    );
    if (!diagnosticsActionResult.success) {
        window.showErrorMessage("Error computing diagnostics for Robot: " + diagnosticsActionResult.message);
        return;
    }

    OUTPUT_CHANNEL.appendLine(diagnosticsActionResult.result);
    workspace.openTextDocument({ "content": diagnosticsActionResult.result }).then((document) => {
        window.showTextDocument(document);
    });
}

function getWorkspaceDescription(wsInfo: WorkspaceInfo) {
    return wsInfo.organizationName + ": " + wsInfo.workspaceName;
}

export async function uploadRobot(robot?: LocalRobotMetadataInfo) {
    // Start this in parallel while we ask the user for info.
    let isLoginNeededPromise: Thenable<ActionResult<boolean>> = commands.executeCommand(
        roboCommands.ROBOCORP_IS_LOGIN_NEEDED_INTERNAL
    );

    let currentUri: Uri;
    if (window.activeTextEditor && window.activeTextEditor.document) {
        currentUri = window.activeTextEditor.document.uri;
    }
    let actionResult: ActionResult<LocalRobotMetadataInfo[]> = await commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );
    if (!actionResult.success) {
        window.showInformationMessage("Error submitting Robot to the Control Room: " + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage(
            "Unable to submit Robot to the Control Room (no Robot detected in the Workspace)."
        );
        return;
    }

    let isLoginNeededActionResult: ActionResult<boolean> = await isLoginNeededPromise;
    if (!isLoginNeededActionResult) {
        window.showInformationMessage("Error getting if login is needed.");
        return;
    }

    if (isLoginNeededActionResult.result) {
        let loggedIn: boolean = await cloudLogin();
        if (!loggedIn) {
            return;
        }
    }

    if (!robot) {
        robot = await askRobotSelection(robotsInfo, "Please select the Robot to upload to the Control Room.");
        if (!robot) {
            return;
        }
    }

    let refresh = false;
    SELECT_OR_REFRESH: do {
        // We ask for the information on the existing workspaces information.
        // Note that this may be cached from the last time it was asked,
        // so, we have an option to refresh it (and ask again).
        let actionResult: ListWorkspacesActionResult = await commands.executeCommand(
            roboCommands.ROBOCORP_CLOUD_LIST_WORKSPACES_INTERNAL,
            { "refresh": refresh }
        );

        if (!actionResult.success) {
            window.showErrorMessage("Error listing Control Room workspaces: " + actionResult.message);
            return;
        }

        let workspaceInfo: WorkspaceInfo[] = actionResult.result;
        if (!workspaceInfo || workspaceInfo.length == 0) {
            window.showErrorMessage("A Control Room Workspace must be created to submit a Robot to the Control Room.");
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
                    "label": "$(folder) " + getWorkspaceDescription(wsInfo),
                    "action": { "filterWorkspaceId": wsInfo.workspaceId },
                };
                captions.push(caption);
            }

            sortCaptions(captions);

            let caption: QuickPickItemWithAction = {
                "label": "$(refresh) * Refresh list",
                "description": "Expected Workspace is not appearing.",
                "sortKey": "09999", // last item
                "action": { "refresh": true },
            };
            captions.push(caption);

            let selectedItem: QuickPickItemWithAction = await showSelectOneQuickPick(
                captions,
                "Please select a Workspace to upload ‘" + robot.name + "’ to."
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
                const wsDesc = getWorkspaceDescription(wsInfo);

                // i.e.: Show the Robots with the same name with more priority in the list.
                let sortKey = "b" + wsDesc;
                if (robotInfo.name == robot.name) {
                    sortKey = "a" + wsDesc;
                }
                let caption: QuickPickItemWithAction = {
                    "label": "$(file) " + robotInfo.name,
                    "description": "(Workspace: " + wsDesc + ")",
                    "sortKey": sortKey,
                    "action": { "existingRobotPackage": robotInfo },
                };
                captions.push(caption);
            }

            const wsDesc = getWorkspaceDescription(wsInfo);
            let caption: QuickPickItemWithAction = {
                "label": "$(new-folder) + Create new Robot",
                "description": "(Workspace: " + wsDesc + ")",
                "sortKey": "c" + wsDesc, // right before last item.
                "action": { "newRobotPackageAtWorkspace": wsInfo },
            };
            captions.push(caption);
        }
        let caption: QuickPickItemWithAction = {
            "label": "$(refresh) * Refresh list",
            "description": "Expected Workspace or Robot is not appearing.",
            "sortKey": "d", // last item
            "action": { "refresh": true },
        };
        captions.push(caption);

        sortCaptions(captions);

        let selectedItem: QuickPickItemWithAction = await showSelectOneQuickPick(
            captions,
            "Update an existing Robot or create a new one."
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
            let yesOverride: string = "Yes";
            let noChooseDifferentTarget: string = "No";
            let cancel: string = "Cancel";
            let robotInfo: PackageInfo = action.existingRobotPackage;

            let updateExistingCaptions: QuickPickItemWithAction[] = new Array();

            let caption: QuickPickItemWithAction = {
                "label": yesOverride,
                "detail": "Override existing Robot",
                "action": yesOverride,
            };
            updateExistingCaptions.push(caption);

            caption = {
                "label": noChooseDifferentTarget,
                "detail": "Go back to choose a different Robot to update",
                "action": noChooseDifferentTarget,
            };
            updateExistingCaptions.push(caption);

            caption = {
                "label": cancel,
                "detail": "Cancel the Robot upload",
                "action": cancel,
            };
            updateExistingCaptions.push(caption);

            let selectedItem: QuickPickItemWithAction = await showSelectOneQuickPick(
                updateExistingCaptions,
                "This will overwrite the robot ‘" + robotInfo.name + "’ on Control Room. Are you sure? "
            );

            // robot.language-server.python
            if (selectedItem.action == noChooseDifferentTarget) {
                refresh = false;
                continue SELECT_OR_REFRESH;
            }
            if (selectedItem.action == cancel) {
                return;
            }
            // selectedItem == yesOverride.
            let actionResult: ActionResult<any> = await commands.executeCommand(
                roboCommands.ROBOCORP_UPLOAD_TO_EXISTING_ROBOT_INTERNAL,
                { "workspaceId": robotInfo.workspaceId, "robotId": robotInfo.id, "directory": robot.directory }
            );

            if (!actionResult.success) {
                let msg: string = "Error uploading to existing Robot: " + actionResult.message;
                OUTPUT_CHANNEL.appendLine(msg);
                window.showErrorMessage(msg);
            } else {
                window.showInformationMessage("Successfully submitted Robot " + robot.name + " to the cloud.");
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

    const RUN_IN_RCC_LRU_CACHE_NAME = "RUN_IN_RCC_LRU_CACHE";
    let runLRU: string[] = await commands.executeCommand(roboCommands.ROBOCORP_LOAD_FROM_DISK_LRU, {
        "name": RUN_IN_RCC_LRU_CACHE_NAME,
    });

    let actionResult: ActionResult<LocalRobotMetadataInfo[]> = await commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );
    if (!actionResult.success) {
        window.showErrorMessage("Error listing Robots: " + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage("Unable to run Robot (no Robot detected in the Workspace).");
        return;
    }

    let items: QuickPickItemRobotTask[] = new Array();

    for (let robotInfo of robotsInfo) {
        let yamlContents = robotInfo.yamlContents;
        let tasks = yamlContents["tasks"];
        if (tasks) {
            let taskNames: string[] = Object.keys(tasks);
            for (let taskName of taskNames) {
                let keyInLRU: string = robotInfo.name + " - " + taskName + " - " + robotInfo.filePath;
                let item: QuickPickItemRobotTask = {
                    "label": "Run robot: " + robotInfo.name + "    Task: " + taskName,
                    "description": robotInfo.filePath,
                    "robotYaml": robotInfo.filePath,
                    "taskName": taskName,
                    "keyInLRU": keyInLRU,
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
        window.showInformationMessage("Unable to run Robot (no Robot detected in the Workspace).");
        return;
    }

    let selectedItem: QuickPickItemRobotTask;
    if (items.length == 1) {
        selectedItem = items[0];
    } else {
        selectedItem = await window.showQuickPick(items, {
            "canPickMany": false,
            "placeHolder": "Please select the Robot and Task to run.",
            "ignoreFocusOut": true,
        });
    }

    if (!selectedItem) {
        return;
    }

    await commands.executeCommand(roboCommands.ROBOCORP_SAVE_IN_DISK_LRU, {
        "name": RUN_IN_RCC_LRU_CACHE_NAME,
        "entry": selectedItem.keyInLRU,
        "lru_size": 3,
    });

    runRobotRCC(noDebug, selectedItem.robotYaml, selectedItem.taskName);
}

export async function runRobotRCC(noDebug: boolean, robotYaml: string, taskName: string) {
    let debugConfiguration: DebugConfiguration = {
        "name": "Config",
        "type": "robocorp-code",
        "request": "launch",
        "robot": robotYaml,
        "task": taskName,
        "args": [],
        "noDebug": noDebug,
    };
    let debugSessionOptions: DebugSessionOptions = {};
    debug.startDebugging(undefined, debugConfiguration, debugSessionOptions);
}

export async function createRobot() {
    let wsFolders: ReadonlyArray<WorkspaceFolder> = workspace.workspaceFolders;
    if (!wsFolders) {
        window.showErrorMessage("Unable to create Robot (no workspace folder is currently opened).");
        return;
    }

    // Start up async calls.
    let asyncListRobotTemplates: Thenable<ActionResult<RobotTemplate[]>> = commands.executeCommand(
        roboCommands.ROBOCORP_LIST_ROBOT_TEMPLATES_INTERNAL
    );

    let asyncListLocalRobots: Thenable<ActionResult<LocalRobotMetadataInfo[]>> = commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );

    let ws: WorkspaceFolder;
    if (wsFolders.length == 1) {
        ws = wsFolders[0];
    } else {
        ws = await window.showWorkspaceFolderPick({
            "placeHolder": "Please select the workspace folder to create the Robot.",
            "ignoreFocusOut": true,
        });
    }
    if (!ws) {
        // Operation cancelled.
        return;
    }

    // Check if we still don't have a Robot in this folder (i.e.: if we have a Robot in the workspace
    // root already, we shouldn't create another Robot inside it).
    try {
        let dirContents: [string, FileType][] = await vscode.workspace.fs.readDirectory(ws.uri);
        for (const element of dirContents) {
            if (element[0] === "robot.yaml") {
                window.showErrorMessage(
                    "It's not possible to create a Robot in: " +
                        ws.uri.fsPath +
                        " because this workspace folder is already a Robot (nested Robots are not allowed)."
                );
                return;
            }
        }
    } catch (error) {
        logError("Error reading contents of: " + ws.uri.fsPath, error, "ACT_CREATE_ROBOT");
    }

    let actionResultListLocalRobots: ActionResult<LocalRobotMetadataInfo[]> = await asyncListLocalRobots;

    let robotsInWorkspace = false;
    if (!actionResultListLocalRobots.success) {
        feedbackRobocorpCodeError("ACT_LIST_ROBOT");
        window.showErrorMessage(
            "Error listing robots: " + actionResultListLocalRobots.message + " (Robot creation will proceed)."
        );
        // This shouldn't happen, but let's proceed as if there were no Robots in the workspace.
    } else {
        let robotsInfo: LocalRobotMetadataInfo[] = actionResultListLocalRobots.result;
        robotsInWorkspace = robotsInfo && robotsInfo.length > 0;
    }

    // Unfortunately vscode does not have a good way to request multiple inputs at once,
    // so, for now we're asking each at a separate step.
    let actionResultListRobotTemplatesInternal: ActionResult<RobotTemplate[]> = await asyncListRobotTemplates;

    if (!actionResultListRobotTemplatesInternal.success) {
        feedbackRobocorpCodeError("ACT_LIST_ROBOT_TEMPLATE");
        window.showErrorMessage("Unable to list Robot templates: " + actionResultListRobotTemplatesInternal.message);
        return;
    }
    let availableTemplates: RobotTemplate[] = actionResultListRobotTemplatesInternal.result;
    if (!availableTemplates) {
        feedbackRobocorpCodeError("ACT_NO_ROBOT_TEMPLATE");
        window.showErrorMessage("Unable to create Robot (the Robot templates could not be loaded).");
        return;
    }

    let selectedItem = await window.showQuickPick(
        availableTemplates.map((robotTemplate) => robotTemplate.description),
        {
            "canPickMany": false,
            "placeHolder": "Please select the template for the Robot.",
            "ignoreFocusOut": true,
        }
    );
    const selectedRobotTemplate = availableTemplates.find(
        (robotTemplate) => robotTemplate.description === selectedItem
    );

    OUTPUT_CHANNEL.appendLine("Selected: " + selectedRobotTemplate?.description);
    if (!selectedRobotTemplate) {
        // Operation cancelled.
        return;
    }

    let useWorkspaceFolder: boolean;
    if (robotsInWorkspace) {
        // i.e.: if we already have robots, this is a multi-Robot workspace.
        useWorkspaceFolder = false;
    } else {
        const USE_WORKSPACE_FOLDER_LABEL = "Use workspace folder";
        let target = await window.showQuickPick(
            [
                { "label": USE_WORKSPACE_FOLDER_LABEL, "detail": "The workspace will only have a single Robot." },
                {
                    "label": "Use child folder in workspace",
                    "detail": "Multiple Robots can be created in this workspace.",
                },
            ],
            {
                "placeHolder": "Where do you want to create the Robot?",
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
            "prompt": "Please provide the name for the Robot folder name.",
            "ignoreFocusOut": true,
        });
        if (!name) {
            // Operation cancelled.
            return;
        }
        targetDir = join(targetDir, name);
    }

    // Now, let's validate if we can indeed create a Robot in the given folder.
    let dirUri = vscode.Uri.file(targetDir);
    let directoryExists = true;
    try {
        let stat = await vscode.workspace.fs.stat(dirUri); // this will raise if the directory doesn't exist.
        if (stat.type == FileType.File) {
            window.showErrorMessage(
                "It's not possible to create a Robot in: " +
                    ws.uri.fsPath +
                    " because this points to a file which already exists (please erase this file and retry)."
            );
            return;
        }
    } catch (err) {
        // ok, directory does not exist
        directoryExists = false;
    }
    let force: boolean = false;
    if (directoryExists) {
        let isEmpty: boolean = true;
        try {
            // The directory already exists, let's see if it's empty (if it's not we need to check
            // whether to force the creation of the Robot).
            let dirContents: [string, FileType][] = await vscode.workspace.fs.readDirectory(dirUri);
            for (const element of dirContents) {
                if (element[0] != ".vscode") {
                    // If there's just a '.vscode', proceed, otherwise,
                    // we need to ask the user about overwriting it.
                    isEmpty = false;
                    break;
                }
            }
        } catch (error) {
            logError("Error reading contents of directory: " + dirUri, error, "ACT_CREATE_ROBOT_LIST_TARGET");
        }
        if (!isEmpty) {
            const CANCEL = "Cancel Robot Creation";
            // Check if the user wants to override the contents.
            let target = await window.showQuickPick(
                [
                    {
                        "label": "Create Robot anyways",
                        "detail": "The Robot will be created and conflicting files will be overwritten.",
                    },
                    {
                        "label": CANCEL,
                        "detail": "No changes will be done.",
                    },
                ],
                {
                    "placeHolder": "The directory is not empty. How do you want to proceed?",
                    "ignoreFocusOut": true,
                }
            );

            if (!target || target["label"] == CANCEL) {
                // Operation cancelled.
                return;
            }
            force = true;
        }
    }

    OUTPUT_CHANNEL.appendLine("Creating Robot at: " + targetDir);
    let createRobotResult: ActionResult<any> = await commands.executeCommand(
        roboCommands.ROBOCORP_CREATE_ROBOT_INTERNAL,
        { "directory": targetDir, "template": selectedRobotTemplate.name, "force": force }
    );

    if (createRobotResult.success) {
        try {
            commands.executeCommand("workbench.files.action.refreshFilesExplorer");
        } catch (error) {
            logError("Error refreshing file explorer.", error, "ACT_REFRESH_FILE_EXPLORER");
        }
        window.showInformationMessage("Robot successfully created in:\n" + targetDir);
    } else {
        OUTPUT_CHANNEL.appendLine("Error creating Robot at: " + targetDir);
        window.showErrorMessage(createRobotResult.message);
    }
}

export async function updateLaunchEnvironment(args): Promise<{ [key: string]: string } | "cancelled"> {
    let robot = args["targetRobot"];
    let environment: { [key: string]: string } = args["env"];
    if (!robot) {
        throw new Error("robot argument is required.");
    }

    if (environment === undefined) {
        throw new Error("env argument is required.");
    }

    let condaPrefix = environment["CONDA_PREFIX"];
    if (!condaPrefix) {
        OUTPUT_CHANNEL.appendLine(
            "Unable to update launch environment for work items because CONDA_PREFIX is not available in the environment:\n" +
                JSON.stringify(environment)
        );
        return environment;
    }

    let work_items_action_result: ActionResultWorkItems = await commands.executeCommand(
        roboCommands.ROBOCORP_LIST_WORK_ITEMS_INTERNAL,
        { "robot": robot, "increment_output": true }
    );

    if (!work_items_action_result || !work_items_action_result.success) {
        return environment;
    }

    let result: WorkItemsInfo = work_items_action_result.result;
    if (!result) {
        return environment;
    }

    // Let's verify that the library is available and has the version we expect.
    let libraryVersionInfoActionResult: LibraryVersionInfoDict;
    try {
        libraryVersionInfoActionResult = await commands.executeCommand(
            roboCommands.ROBOCORP_VERIFY_LIBRARY_VERSION_INTERNAL,
            {
                "conda_prefix": condaPrefix,
                "library": "rpaframework",
                "version": "11.3",
            }
        );
    } catch (error) {
        logError("Error updating launch environment.", error, "ACT_UPDATE_LAUNCH_ENV");
        return environment;
    }

    if (!libraryVersionInfoActionResult["success"]) {
        OUTPUT_CHANNEL.appendLine(
            "Launch environment for work items not updated. Reason: " + libraryVersionInfoActionResult.message
        );
        return environment;
    }

    // If we have found the robot, we should have the result and thus we should always set the
    // RPA_OUTPUT_WORKITEM_PATH (even if we don't have any input, we'll set to where we want
    // to save items).
    let newEnv: { [key: string]: string } = { ...environment };

    newEnv["RPA_OUTPUT_WORKITEM_PATH"] = result.new_output_workitem_path;
    newEnv["RPA_WORKITEMS_ADAPTER"] = "RPA.Robocorp.WorkItems.FileAdapter";

    const input_work_items = result.input_work_items;
    const output_work_items = result.output_work_items;
    if (input_work_items.length > 0 || output_work_items.length > 0) {
        // If we have any input for this Robot, present it to the user.

        let items: QuickPickItemWithAction[] = []; // Note: just use the action as a 'data'.
        let noWorkItemLabel = "<No work item as input>";
        items.push({
            "label": "<No work item as input>",
            "action": undefined,
        });

        for (const it of input_work_items) {
            items.push({
                "label": it.name,
                "detail": "Input",
                "action": it.json_path,
            });
        }

        for (const it of output_work_items) {
            items.push({
                "label": it.name,
                "detail": "Output",
                "action": it.json_path,
            });
        }

        let selectedItem = await showSelectOneQuickPick(
            items,
            "Please select the work item input to be used by RPA.Robocorp.WorkItems."
        );
        if (!selectedItem) {
            return "cancelled";
        }
        if (selectedItem.label === noWorkItemLabel) {
            return newEnv;
        }

        // No need to await.
        feedback("vscode.workitem.input.selected");

        newEnv["RPA_INPUT_WORKITEM_PATH"] = selectedItem.action;
    }

    return newEnv;
}
