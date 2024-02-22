import {
    TREE_VIEW_ROBOCORP_CLOUD_TREE,
    TREE_VIEW_ROBOCORP_PACKAGE_CONTENT_TREE,
    TREE_VIEW_ROBOCORP_TASK_PACKAGES_TREE,
    TREE_VIEW_ROBOCORP_PACKAGE_RESOURCES_TREE,
} from "./robocorpViews";
import * as vscode from "vscode";
import { ExtensionContext } from "vscode";
import { runRobotRCC, uploadRobot } from "./activities";
import { createRccTerminal } from "./rccTerminal";
import { RobotContentTreeDataProvider } from "./viewsRobotContent";
import {
    debounce,
    getSelectedRobot,
    onSelectedRobotChanged,
    refreshTreeView,
    RobotEntry,
    RobotEntryType,
    setSelectedRobot,
    treeViewIdToTreeDataProvider,
    treeViewIdToTreeView,
} from "./viewsCommon";
import { CloudTreeDataProvider } from "./viewsRobocorp";
import { RobotsTreeDataProvider } from "./viewsRobots";
import { ResourcesTreeDataProvider } from "./viewsResources";
import * as path from "path";
import { fileExists, makeDirs, uriExists, verifyFileExists } from "./files";
import { QuickPickItemWithAction, showSelectOneQuickPick } from "./ask";
import { slugify } from "./slugify";
import { OUTPUT_CHANNEL } from "./channel";

function empty<T>(array: readonly T[]) {
    return array === undefined || array.length === 0;
}

export async function openRobotTreeSelection(robot?: RobotEntry) {
    if (!robot) {
        robot = getSelectedRobot();
    }
    if (robot) {
        vscode.window.showTextDocument(robot.uri);
    }
}

export async function openRobotCondaTreeSelection(robot?: RobotEntry) {
    if (!robot) {
        robot = getSelectedRobot();
    }
    if (robot) {
        const yamlContents = robot.robot.yamlContents;
        if (yamlContents) {
            const condaConfigFile = yamlContents["condaConfigFile"];
            if (condaConfigFile) {
                vscode.window.showTextDocument(vscode.Uri.file(path.join(robot.robot.directory, condaConfigFile)));
                return;
            }
        }

        // It didn't return: let's just check for a conda.yaml.
        const condaYamlPath = path.join(robot.robot.directory, "conda.yaml");
        const condaYamlUri = vscode.Uri.file(condaYamlPath);
        if (await uriExists(condaYamlUri)) {
            vscode.window.showTextDocument(condaYamlUri);
            return;
        }
    }
}

export async function openPackageTreeSelection(robot?: RobotEntry) {
    if (!robot) {
        robot = getSelectedRobot();
    }
    if (robot) {
        const packageYamlPath = path.join(robot.robot.directory, "package.yaml");
        const packageYamlUri = vscode.Uri.file(packageYamlPath);
        if (await uriExists(packageYamlUri)) {
            vscode.window.showTextDocument(packageYamlUri);
            return;
        }
    }
}

export async function openLocatorsJsonTreeSelection() {
    // Json
    const robot = getSelectedRobot();
    if (robot) {
        let locatorJson = path.join(robot.robot.directory, "locators.json");
        if (verifyFileExists(locatorJson, false)) {
            vscode.window.showTextDocument(vscode.Uri.file(locatorJson));
        }
    }
}

export async function cloudUploadRobotTreeSelection(robot?: RobotEntry) {
    if (!robot) {
        robot = getSelectedRobot();
    }
    if (robot) {
        uploadRobot(robot.robot);
    }
}

export async function createRccTerminalTreeSelection(robot?: RobotEntry) {
    if (!robot) {
        robot = getSelectedRobot();
    }
    if (robot) {
        createRccTerminal(robot.robot);
    }
}

export async function runSelectedRobot(noDebug: boolean, taskRobotEntry?: RobotEntry) {
    if (!taskRobotEntry) {
        taskRobotEntry = await getSelectedRobot({
            noSelectionMessage: "Unable to make launch (Task not selected in Packages Tree).",
            moreThanOneSelectionMessage: "Unable to make launch -- only 1 task must be selected.",
        });
    }
    runRobotRCC(noDebug, taskRobotEntry.robot.filePath, taskRobotEntry.taskName);
}

async function createDefaultInputJson(inputUri: vscode.Uri) {
    await vscode.workspace.fs.writeFile(
        inputUri,
        Buffer.from(`{
    "paramName": "paramValue"
}`)
    );
}

export async function openAction(actionRobotEntry?: RobotEntry) {
    const range = actionRobotEntry.range;
    if (range) {
        const selection: vscode.Range = new vscode.Range(
            new vscode.Position(range.start.line - 1, range.start.character),
            new vscode.Position(range.end.line - 1, range.end.character)
        );
        await vscode.window.showTextDocument(actionRobotEntry.uri, { selection: selection });
    } else {
        await vscode.window.showTextDocument(actionRobotEntry.uri);
    }
}

export async function editInput(actionRobotEntry?: RobotEntry) {
    if (!actionRobotEntry) {
        vscode.window.showErrorMessage("Unable to edit input: no target action entry defined for action.");
        return;
    }
    const targetInput = await getTargetInputJson(actionRobotEntry);
    const inputUri = vscode.Uri.file(targetInput);
    if (!(await fileExists(targetInput))) {
        await createDefaultInputJson(inputUri);
    }
    await vscode.window.showTextDocument(inputUri);
}

export async function getTargetInputJson(actionRobotEntry: RobotEntry): Promise<string> {
    const nameSlugified = slugify(actionRobotEntry.actionName);

    const dir = actionRobotEntry.robot.directory;
    const devDataDir = path.join(dir, "devdata");
    await makeDirs(devDataDir);
    const targetInput = path.join(devDataDir, `input_${nameSlugified}.json`);
    return targetInput;
}

export async function runSelectedAction(noDebug: boolean, actionRobotEntry?: RobotEntry) {
    if (!actionRobotEntry) {
        actionRobotEntry = await getSelectedRobot({
            noSelectionMessage: "Unable to make launch (Action not selected in Packages Tree).",
            moreThanOneSelectionMessage: "Unable to make launch -- only 1 action must be selected.",
        });
        if (!actionRobotEntry) {
            return;
        }
    }

    if (!actionRobotEntry.actionName) {
        vscode.window.showErrorMessage("actionName not available in entry to launch.");
        return;
    }

    // The input must be asked when running actions in this case and it should be
    // saved in 'devdata/input_xxx.json'
    const nameSlugified = slugify(actionRobotEntry.actionName);
    const targetInput = await getTargetInputJson(actionRobotEntry);

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
            `Customize input for the ${actionRobotEntry.actionName} action`
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
        "package": actionRobotEntry.robot.filePath,
        "uri": actionRobotEntry.uri.toString(),
        "jsonInput": targetInput,
        "actionName": actionRobotEntry.actionName,
        "args": [],
        "noDebug": noDebug,
    };
    let debugSessionOptions: vscode.DebugSessionOptions = {};
    vscode.debug.startDebugging(undefined, debugConfiguration, debugSessionOptions);
}

async function onChangedRobotSelection(
    robotsTree: vscode.TreeView<RobotEntry>,
    treeDataProvider: RobotsTreeDataProvider,
    selection: readonly RobotEntry[]
) {
    if (selection === undefined) {
        selection = [];
    }
    // Remove error nodes from the selection.
    selection = selection.filter((e) => {
        return e.type != RobotEntryType.Error;
    });

    if (empty(selection)) {
        let rootChildren: RobotEntry[] = await treeDataProvider.getValidCachedOrComputeChildren(undefined);
        if (empty(rootChildren)) {
            // i.e.: there's nothing to reselect, so, just notify as usual.
            setSelectedRobot(undefined);
            return;
        }

        // Automatically update selection / reselect some item.
        setSelectedRobot(rootChildren[0]);
        robotsTree.reveal(rootChildren[0], { "select": true });
        return;
    }

    if (!empty(selection)) {
        setSelectedRobot(selection[0]);
        return;
    }

    let rootChildren: RobotEntry[] = await treeDataProvider.getValidCachedOrComputeChildren(undefined);
    if (empty(rootChildren)) {
        // i.e.: there's nothing to reselect, so, just notify as usual.
        setSelectedRobot(undefined);
        return;
    }

    // // Automatically update selection / reselect some item.
    setSelectedRobot(rootChildren[0]);
    robotsTree.reveal(rootChildren[0], { "select": true });
}

export function registerViews(context: ExtensionContext) {
    // Cloud data
    let cloudTreeDataProvider = new CloudTreeDataProvider();
    let viewsCloudTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_CLOUD_TREE, {
        "treeDataProvider": cloudTreeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_CLOUD_TREE, viewsCloudTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_CLOUD_TREE, cloudTreeDataProvider);

    // Robots (i.e.: list of robots, not its contents)
    let robotsTreeDataProvider = new RobotsTreeDataProvider();
    let robotsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_TASK_PACKAGES_TREE, {
        "treeDataProvider": robotsTreeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_TASK_PACKAGES_TREE, robotsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_TASK_PACKAGES_TREE, robotsTreeDataProvider);

    context.subscriptions.push(
        robotsTree.onDidChangeSelection(
            async (e) => await onChangedRobotSelection(robotsTree, robotsTreeDataProvider, e.selection)
        )
    );

    context.subscriptions.push(
        robotsTreeDataProvider.onForceSelectionFromTreeData(
            async (e) => await onChangedRobotSelection(robotsTree, robotsTreeDataProvider, robotsTree.selection)
        )
    );

    // Update contexts when the current robot changes.
    context.subscriptions.push(
        onSelectedRobotChanged(async (robotEntry: RobotEntry | undefined) => {
            if (!robotEntry) {
                vscode.commands.executeCommand("setContext", "robocorp-code:single-task-selected", false);
                vscode.commands.executeCommand("setContext", "robocorp-code:single-robot-selected", false);
                return;
            }
            vscode.commands.executeCommand(
                "setContext",
                "robocorp-code:single-task-selected",
                robotEntry.type == RobotEntryType.Task
            );
            vscode.commands.executeCommand("setContext", "robocorp-code:single-robot-selected", true);
        })
    );

    // The contents of a single robot (the one selected in the Robots tree).
    let robotContentTreeDataProvider = new RobotContentTreeDataProvider();
    let robotContentTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_PACKAGE_CONTENT_TREE, {
        "treeDataProvider": robotContentTreeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_PACKAGE_CONTENT_TREE, robotContentTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_PACKAGE_CONTENT_TREE, robotContentTreeDataProvider);

    context.subscriptions.push(
        onSelectedRobotChanged((e) => robotContentTreeDataProvider.onRobotsTreeSelectionChanged(e))
    );
    context.subscriptions.push(
        robotContentTreeDataProvider.onForceSelectionFromTreeData(
            async (e) => await onChangedRobotSelection(robotsTree, robotsTreeDataProvider, robotsTree.selection)
        )
    );

    // Resources
    let resourcesDataProvider = new ResourcesTreeDataProvider();
    let resourcesTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_PACKAGE_RESOURCES_TREE, {
        "treeDataProvider": resourcesDataProvider,
        "canSelectMany": true,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_PACKAGE_RESOURCES_TREE, resourcesTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_PACKAGE_RESOURCES_TREE, resourcesDataProvider);

    context.subscriptions.push(onSelectedRobotChanged((e) => resourcesDataProvider.onRobotsTreeSelectionChanged(e)));

    let robotsWatcher: vscode.FileSystemWatcher = vscode.workspace.createFileSystemWatcher("**/robot.yaml");

    let onChangeRobotsYaml = debounce(() => {
        // Note: this doesn't currently work if the parent folder is renamed or removed.
        // (https://github.com/microsoft/vscode/pull/110858)
        refreshTreeView(TREE_VIEW_ROBOCORP_TASK_PACKAGES_TREE);
    }, 300);

    robotsWatcher.onDidChange(onChangeRobotsYaml);
    robotsWatcher.onDidCreate(onChangeRobotsYaml);
    robotsWatcher.onDidDelete(onChangeRobotsYaml);

    let locatorsWatcher: vscode.FileSystemWatcher = vscode.workspace.createFileSystemWatcher("**/locators.json");

    let onChangeLocatorsJson = debounce(() => {
        // Note: this doesn't currently work if the parent folder is renamed or removed.
        // (https://github.com/microsoft/vscode/pull/110858)
        refreshTreeView(TREE_VIEW_ROBOCORP_PACKAGE_RESOURCES_TREE);
    }, 300);

    locatorsWatcher.onDidChange(onChangeLocatorsJson);
    locatorsWatcher.onDidCreate(onChangeLocatorsJson);
    locatorsWatcher.onDidDelete(onChangeLocatorsJson);

    context.subscriptions.push(robotsTree);
    context.subscriptions.push(resourcesTree);
    context.subscriptions.push(robotsWatcher);
    context.subscriptions.push(locatorsWatcher);
}
