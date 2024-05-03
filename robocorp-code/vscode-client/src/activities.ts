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
import {
    QuickPickItemWithAction,
    sortCaptions,
    QuickPickItemRobotTask,
    showSelectOneQuickPick,
    getWorkspaceDescription,
    selectWorkspace,
    showSelectOneStrQuickPick,
    askForWs,
} from "./ask";
import { feedback, feedbackRobocorpCodeError, getEndpointUrl } from "./rcc";
import { refreshCloudTreeView } from "./viewsRobocorp";
import {
    ActionResult,
    ActionResultWorkItems,
    InterpreterInfo,
    IVaultInfo,
    LibraryVersionInfoDict,
    LocalRobotMetadataInfo,
    PackageInfo,
    RobotTemplate,
    WorkItemsInfo,
    WorkspaceInfo,
} from "./protocols";
import { envVarsForOutViewIntegration } from "./output/outViewRunIntegration";
import { connectWorkspace } from "./vault";
import {
    areThereRobotsInWorkspace,
    isActionPackage,
    isDirectoryAPackageDirectory,
    verifyIfPathOkToCreatePackage,
} from "./common";

export interface ListOpts {
    showTaskPackages: boolean;
    showActionPackages: boolean;
}

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
            const cloudBaseUrl = await getEndpointUrl("cloud-ui");
            env.openExternal(Uri.parse(cloudBaseUrl + "settings/access-credentials"));
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

    const doConnectToWorkspace = await showSelectOneStrQuickPick(
        ["Yes", "No"],
        "Linked account. Connect to a workspace to access related Vault Secrets and Storage?"
    );
    if (doConnectToWorkspace === "Yes") {
        const checkLogin = false; // no need to check login, we just logged in.
        await connectWorkspace(checkLogin);
    }

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
        if (interpreter === null || (typeof interpreter === "string" && interpreter === "null")) {
            throw Error("Interpreter not found. Retrying call...");
        }
        return { "success": true, "message": "", "result": interpreter };
    } catch (error) {
        // We couldn't resolve with the robotframework language server command, fallback to the robocorp code command.
        try {
            let interpreter: ActionResult<InterpreterInfo | undefined> = await commands.executeCommand(
                roboCommands.ROBOCORP_RESOLVE_INTERPRETER,
                {
                    "target_robot": targetRobot,
                }
            );
            if (interpreter === null || (typeof interpreter === "string" && interpreter === "null")) {
                throw Error("Interpreter not found");
            }
            return interpreter;
        } catch (error) {
            logError("Error resolving interpreter.", error, "ACT_RESOLVE_INTERPRETER");
            return { "success": false, "message": "Unable to resolve interpreter.", "result": undefined };
        }
    }
}

export async function listAndAskRobotSelection(
    selectionMessage: string,
    noRobotErrorMessage: string,
    opts: ListOpts
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

    const filter = (entry: LocalRobotMetadataInfo) => {
        const isActionPkg = isActionPackage(entry);
        const isTaskPackage = !isActionPkg;

        if (!opts.showActionPackages && isActionPkg) {
            return false;
        }
        if (!opts.showTaskPackages && isTaskPackage) {
            return false;
        }
        return true;
    };

    robotsInfo = robotsInfo.filter(filter);
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
        window.showInformationMessage("Error listing existing packages: " + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage(
            "Unable to set Python extension interpreter (no Action nor Task Package detected in the Workspace)."
        );
        return;
    }

    let robot: LocalRobotMetadataInfo = await askRobotSelection(
        robotsInfo,
        "Please select the Action or Task Package from which the python executable should be used."
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
    if (robotsInfo) {
        // Only use task packages.
        robotsInfo = robotsInfo.filter((r) => {
            return !isActionPackage(r);
        });
    }

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage(
            "No Task Package detected in the Workspace. If a robot.yaml is available, open it for more information."
        );
        return;
    }

    let robot = await askRobotSelection(robotsInfo, "Please select the Task Package to analyze.");
    if (!robot) {
        return;
    }

    let diagnosticsActionResult: ActionResult<string> = await commands.executeCommand(
        roboCommands.ROBOCORP_CONFIGURATION_DIAGNOSTICS_INTERNAL,
        { "robotYaml": robot.filePath }
    );
    if (!diagnosticsActionResult.success) {
        window.showErrorMessage("Error computing diagnostics for Task Package: " + diagnosticsActionResult.message);
        return;
    }

    OUTPUT_CHANNEL.appendLine(diagnosticsActionResult.result);
    workspace.openTextDocument({ "content": diagnosticsActionResult.result }).then((document) => {
        window.showTextDocument(document);
    });
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
        window.showInformationMessage("Error submitting Task Package (Robot) to Control Room: " + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;
    if (robotsInfo) {
        robotsInfo = robotsInfo.filter((r) => {
            return !isActionPackage(r);
        });
    }

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage(
            "Unable to submit Task Package (Robot) to Control Room (no Task Package detected in the Workspace)."
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
        robot = await askRobotSelection(
            robotsInfo,
            "Please select the Task Package (Robot) to upload to the Control Room."
        );
        if (!robot) {
            return;
        }
    }

    let refresh = false;
    SELECT_OR_REFRESH: do {
        let workspaceSelection = await selectWorkspace(
            "Please select a Workspace to upload ‘" + robot.name + "’ to.",
            refresh
        );
        if (workspaceSelection === undefined) {
            return;
        }

        const workspaceInfo = workspaceSelection.workspaceInfo;
        const workspaceIdFilter = workspaceSelection.selectedWorkspaceInfo.workspaceId;

        // -------------------------------------------------------
        // Select Robot/New Robot/Refresh
        // -------------------------------------------------------

        let captions: QuickPickItemWithAction[] = new Array();
        for (let i = 0; i < workspaceInfo.length; i++) {
            const wsInfo: WorkspaceInfo = workspaceInfo[i];

            if (workspaceIdFilter != wsInfo.workspaceId) {
                continue;
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
        window.showErrorMessage("Error listing Task Packages (Robots): " + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;
    if (robotsInfo) {
        robotsInfo = robotsInfo.filter((r) => {
            return !isActionPackage(r);
        });
    }

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage(
            "Unable to run Task Package (Robot) (no Task Package detected in the Workspace)."
        );
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
        window.showInformationMessage(
            "Unable to run Task Package (Robot) (no Task Package detected in the Workspace)."
        );
        return;
    }

    let selectedItem: QuickPickItemRobotTask;
    if (items.length == 1) {
        selectedItem = items[0];
    } else {
        selectedItem = await window.showQuickPick(items, {
            "canPickMany": false,
            "placeHolder": "Please select the Task Package (Robot) and Task to run.",
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
    // Start up async calls.
    let asyncListRobotTemplates: Thenable<ActionResult<RobotTemplate[]>> = commands.executeCommand(
        roboCommands.ROBOCORP_LIST_ROBOT_TEMPLATES_INTERNAL
    );

    const robotsInWorkspacePromise: Promise<boolean> = areThereRobotsInWorkspace();
    let ws: WorkspaceFolder | undefined = await askForWs();
    if (!ws) {
        // Operation cancelled.
        return;
    }

    if (await isDirectoryAPackageDirectory(ws.uri)) {
        return;
    }

    // Unfortunately vscode does not have a good way to request multiple inputs at once,
    // so, for now we're asking each at a separate step.
    let actionResultListRobotTemplatesInternal: ActionResult<RobotTemplate[]> = await asyncListRobotTemplates;

    if (!actionResultListRobotTemplatesInternal.success) {
        feedbackRobocorpCodeError("ACT_LIST_ROBOT_TEMPLATE");
        window.showErrorMessage(
            "Unable to list Task Package templates: " + actionResultListRobotTemplatesInternal.message
        );
        return;
    }
    let availableTemplates: RobotTemplate[] = actionResultListRobotTemplatesInternal.result;
    if (!availableTemplates) {
        feedbackRobocorpCodeError("ACT_NO_ROBOT_TEMPLATE");
        window.showErrorMessage("Unable to create Task Package (the Task Package templates could not be loaded).");
        return;
    }

    let selectedItem = await window.showQuickPick(
        availableTemplates.map((robotTemplate) => robotTemplate.description),
        {
            "canPickMany": false,
            "placeHolder": "Please select the template for the Task Package.",
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
                    "detail": "The workspace will only have a single Task Package.",
                },
                {
                    "label": "Use child folder in workspace (advanced)",
                    "detail": "Multiple Task Packages can be created in this workspace.",
                },
            ],
            {
                "placeHolder": "Where do you want to create the Task Package?",
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
            "prompt": "Please provide the name for the Task Package (Robot) folder name.",
            "ignoreFocusOut": true,
        });
        if (!name) {
            // Operation cancelled.
            return;
        }
        targetDir = join(targetDir, name);
    }

    // Now, let's validate if we can indeed create a Robot in the given folder.
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

    OUTPUT_CHANNEL.appendLine("Creating Task Package (Robot) at: " + targetDir);
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
        window.showInformationMessage("Task Package (Robot) successfully created in:\n" + targetDir);
    } else {
        OUTPUT_CHANNEL.appendLine("Error creating Task Package (Robot) at: " + targetDir);
        window.showErrorMessage(createRobotResult.message);
    }
}

export async function updateLaunchEnvironment(args): Promise<{ [key: string]: string } | "cancelled"> {
    OUTPUT_CHANNEL.appendLine(`updateLaunchEnvironment for ${args["targetRobot"]}.`);
    let newEnv: any;
    try {
        newEnv = await updateLaunchEnvironmentPart0(args);
    } catch (error) {
        let msg = "It was not possible to build the Robot launch environment for the launch.";
        if (error && error.message) {
            msg += ` (${error.message})`;
        }
        msg += "See OUTPUT > Robocorp Code for more details.";
        window.showErrorMessage(msg);
        logError("Error computing launch env.", error, "ERROR_LAUNCH_ENV");
        throw error;
    }
    if (newEnv !== "cancelled") {
        try {
            // Ok, also check for pre-run scripts.
            const hasPreRunScripts = await commands.executeCommand(roboCommands.ROBOCORP_HAS_PRE_RUN_SCRIPTS_INTERNAL, {
                "robot": args["targetRobot"],
            });
            if (hasPreRunScripts) {
                OUTPUT_CHANNEL.appendLine(`preRunScripts found for ${args["targetRobot"]}.`);
                const runPreRunScripts = async () =>
                    await window.withProgress(
                        {
                            location: vscode.ProgressLocation.Notification,
                            title: "Running preRunScripts (see 'OUTPUT > Robocorp Code' for details).",
                            cancellable: false,
                        },
                        async (
                            progress: vscode.Progress<{ message?: string; increment?: number }>,
                            token: vscode.CancellationToken
                        ): Promise<void> => {
                            let result = await commands.executeCommand(
                                roboCommands.ROBOCORP_RUN_PRE_RUN_SCRIPTS_INTERNAL,
                                {
                                    "robot": args["targetRobot"],
                                    "env": newEnv,
                                }
                            );
                            if (result) {
                                if (!result["success"]) {
                                    OUTPUT_CHANNEL.show();
                                    window.showErrorMessage(
                                        "There was a problem running preRunScripts. See `OUTPUT > Robocorp Code` for more details."
                                    );
                                }
                            }
                        }
                    );
                await runPreRunScripts();
            } else {
                OUTPUT_CHANNEL.appendLine(`preRunScripts NOT found for ${args["targetRobot"]}.`);
            }
        } catch (error) {
            logError("Error checking or executing preRunScripts.", error, "ERR_PRE_RUN_SCRIPTS");
        }
    }
    return newEnv;
}

export async function updateLaunchEnvironmentPart0(args): Promise<{ [key: string]: string } | "cancelled"> {
    let robot = args["targetRobot"];
    // Note: the 'robot' may not be the robot.yaml, it may be a .robot or a .py
    // which is about to be launched (the robot.yaml must be derived from it).
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

    // Note: we need to update the environment for:
    // - Vault
    // - Work items

    let newEnv: { [key: string]: string } = { ...environment };
    for (const [key, val] of envVarsForOutViewIntegration) {
        newEnv[key] = val;
    }

    let vaultInfoActionResult: ActionResult<IVaultInfo> = await commands.executeCommand(
        roboCommands.ROBOCORP_GET_CONNECTED_VAULT_WORKSPACE_INTERNAL
    );
    if (vaultInfoActionResult?.success) {
        const vaultInfo: IVaultInfo = vaultInfoActionResult.result;
        if (vaultInfo?.workspaceId) {
            // The workspace vault is connected, so, we must authorize it...
            let vaultInfoEnvActionResult: ActionResult<{ [key: string]: string }> = await commands.executeCommand(
                roboCommands.ROBOCORP_UPDATE_LAUNCH_ENV_GET_VAULT_ENV_INTERNAL
            );
            if (!vaultInfoEnvActionResult.success) {
                throw new Error(
                    "It was not possible to connect to the vault while launching for: " +
                        getWorkspaceDescription(vaultInfo) +
                        ".\nDetails: " +
                        vaultInfoEnvActionResult.message
                );
            }

            for (const [key, value] of Object.entries(vaultInfoEnvActionResult.result)) {
                newEnv[key] = value;
            }
        }
    }

    let workItemsActionResult: ActionResultWorkItems = await commands.executeCommand(
        roboCommands.ROBOCORP_LIST_WORK_ITEMS_INTERNAL,
        { "robot": robot, "increment_output": true }
    );

    if (!workItemsActionResult || !workItemsActionResult.success) {
        OUTPUT_CHANNEL.appendLine(`Unable to get work items: ${JSON.stringify(workItemsActionResult)}`);
        return newEnv;
    }

    let result: WorkItemsInfo = workItemsActionResult.result;
    if (!result) {
        return newEnv;
    }

    // Let's verify that the library is available and has the version we expect.
    let libraryVersionInfoActionResult: LibraryVersionInfoDict;
    try {
        libraryVersionInfoActionResult = await commands.executeCommand(
            roboCommands.ROBOCORP_VERIFY_LIBRARY_VERSION_INTERNAL,
            {
                "conda_prefix": condaPrefix,
                "libs_and_version": [
                    ["rpaframework", "11.3"],
                    ["robocorp-workitems", "0.0.1"], // Any version will do
                ],
            }
        );
    } catch (error) {
        logError("Error updating launch environment.", error, "ACT_UPDATE_LAUNCH_ENV");
        return newEnv;
    }

    if (!libraryVersionInfoActionResult["success"]) {
        OUTPUT_CHANNEL.appendLine(
            "Launch environment for work items not updated. Reason: " + libraryVersionInfoActionResult.message
        );
        return newEnv;
    }

    // If we have found the robot, we should have the result and thus we should always set the
    // RPA_OUTPUT_WORKITEM_PATH (even if we don't have any input, we'll set to where we want
    // to save items).

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
