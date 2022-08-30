import {
    TREE_VIEW_ROBOCORP_CLOUD_TREE,
    TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE,
    TREE_VIEW_ROBOCORP_ROBOTS_TREE,
    TREE_VIEW_ROBOCORP_RESOURCES_TREE,
} from "./robocorpViews";
import * as vscode from "vscode";
import { ExtensionContext } from "vscode";
import { runRobotRCC, uploadRobot } from "./activities";
import { createRccTerminal } from "./rccTerminal";
import { RobotContentTreeDataProvider } from "./viewsRobotContent";
import { WorkItemsTreeDataProvider } from "./viewsWorkItems";
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
import { LocatorsTreeDataProvider } from "./viewsLocators";
import { ResourcesTreeDataProvider } from "./viewsResources";

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
            noSelectionMessage: "Unable to make launch (Robot task not selected in Robots Tree).",
            moreThanOneSelectionMessage: "Unable to make launch -- only 1 task must be selected.",
        });
    }
    runRobotRCC(noDebug, taskRobotEntry.robot.filePath, taskRobotEntry.taskName);
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
    let robotsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE, {
        "treeDataProvider": robotsTreeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, robotsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, robotsTreeDataProvider);

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
    let robotContentTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE, {
        "treeDataProvider": robotContentTreeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE, robotContentTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE, robotContentTreeDataProvider);

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
    let resourcesTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_RESOURCES_TREE, {
        "treeDataProvider": resourcesDataProvider,
        "canSelectMany": true,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_RESOURCES_TREE, resourcesTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_RESOURCES_TREE, resourcesDataProvider);

    context.subscriptions.push(onSelectedRobotChanged((e) => resourcesDataProvider.onRobotsTreeSelectionChanged(e)));

    let robotsWatcher: vscode.FileSystemWatcher = vscode.workspace.createFileSystemWatcher("**/robot.yaml");

    let onChangeRobotsYaml = debounce(() => {
        // Note: this doesn't currently work if the parent folder is renamed or removed.
        // (https://github.com/microsoft/vscode/pull/110858)
        refreshTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
    }, 300);

    robotsWatcher.onDidChange(onChangeRobotsYaml);
    robotsWatcher.onDidCreate(onChangeRobotsYaml);
    robotsWatcher.onDidDelete(onChangeRobotsYaml);

    let locatorsWatcher: vscode.FileSystemWatcher = vscode.workspace.createFileSystemWatcher("**/locators.json");

    let onChangeLocatorsJson = debounce(() => {
        // Note: this doesn't currently work if the parent folder is renamed or removed.
        // (https://github.com/microsoft/vscode/pull/110858)
        refreshTreeView(TREE_VIEW_ROBOCORP_RESOURCES_TREE);
    }, 300);

    locatorsWatcher.onDidChange(onChangeLocatorsJson);
    locatorsWatcher.onDidCreate(onChangeLocatorsJson);
    locatorsWatcher.onDidDelete(onChangeLocatorsJson);

    context.subscriptions.push(robotsTree);
    context.subscriptions.push(resourcesTree);
    context.subscriptions.push(robotsWatcher);
    context.subscriptions.push(locatorsWatcher);
}
