import {
    TREE_VIEW_ROBOCORP_CLOUD_TREE,
    TREE_VIEW_ROBOCORP_LOCATORS_TREE,
    TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE,
    TREE_VIEW_ROBOCORP_ROBOTS_TREE,
    // TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE,
} from "./robocorpViews";
import * as vscode from "vscode";
import { ExtensionContext } from "vscode";
import * as roboCommands from "./robocorpCommands";
import { OUTPUT_CHANNEL } from "./channel";
import { runRobotRCC, uploadRobot } from "./activities";
import { createRccTerminal } from "./rccTerminal";
import { RobotContentTreeDataProvider } from "./viewsRobotContent";
import { WorkItemsTreeDataProvider } from "./viewsWorkItems";
import {
    basename,
    CloudEntry,
    debounce,
    getSelectedRobot,
    LocatorEntry,
    RobotEntry,
    RobotEntryType,
    treeViewIdToTreeDataProvider,
    treeViewIdToTreeView,
} from "./viewsCommon";
import { ROBOCORP_SUBMIT_ISSUE } from "./robocorpCommands";

function getRobotLabel(robotInfo: LocalRobotMetadataInfo): string {
    let label: string = undefined;
    if (robotInfo.yamlContents) {
        label = robotInfo.yamlContents["name"];
    }
    if (!label) {
        if (robotInfo.directory) {
            label = basename(robotInfo.directory);
        }
    }
    if (!label) {
        label = "";
    }
    return label;
}

let _globalSentMetric: boolean = false;

export class CloudTreeDataProvider implements vscode.TreeDataProvider<CloudEntry> {
    private _onDidChangeTreeData: vscode.EventEmitter<CloudEntry | null> = new vscode.EventEmitter<CloudEntry | null>();
    readonly onDidChangeTreeData: vscode.Event<CloudEntry | null> = this._onDidChangeTreeData.event;

    public refreshOnce = false;

    fireRootChange() {
        this._onDidChangeTreeData.fire(null);
    }

    async getChildren(element?: CloudEntry): Promise<CloudEntry[]> {
        if (!element) {
            let accountInfoResult: ActionResult = await vscode.commands.executeCommand(
                roboCommands.ROBOCORP_GET_LINKED_ACCOUNT_INFO_INTERNAL
            );
            let ret: CloudEntry[] = [];
            if (!accountInfoResult.success) {
                ret.push({
                    "label": "Link to Control Room",
                    "iconPath": "link",
                    "viewItemContextValue": "cloudLoginItem",
                    "command": {
                        "title": "Link to Control Room",
                        "command": roboCommands.ROBOCORP_CLOUD_LOGIN,
                    },
                });
            } else {
                let accountInfo = accountInfoResult.result;
                ret.push({
                    "label": "Linked: " + accountInfo["fullname"] + " (" + accountInfo["email"] + ")",
                    "iconPath": "link",
                    "viewItemContextValue": "cloudLogoutItem",
                });
            }
            ret.push({
                "label": "Robot Developer Guide",
                "iconPath": "book",
                "command": {
                    "title": "Open https://robocorp.com/docs/development-guide",
                    "command": "vscode.open",
                    "arguments": [vscode.Uri.parse("https://robocorp.com/docs/development-guide")],
                },
            });
            ret.push({
                "label": "RPA Framework Library",
                "iconPath": "notebook",
                "command": {
                    "title": "Open https://robocorp.com/docs/libraries",
                    "command": "vscode.open",
                    "arguments": [vscode.Uri.parse("https://robocorp.com/docs/libraries")],
                },
            });
            ret.push({
                "label": "Submit Issue",
                "iconPath": "report",
                "command": {
                    "title": "Submit Issue",
                    "command": ROBOCORP_SUBMIT_ISSUE,
                },
            });

            return ret;
        }
        if (element.children) {
            return element.children;
        }
        return [];
    }

    getTreeItem(element: CloudEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(
            element.label,
            element.children ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None
        );
        treeItem.command = element.command;
        treeItem.iconPath = new vscode.ThemeIcon(element.iconPath);
        if (element.viewItemContextValue) {
            treeItem.contextValue = element.viewItemContextValue;
        }
        return treeItem;
    }
}

export class RobotsTreeDataProvider implements vscode.TreeDataProvider<RobotEntry> {
    private _onDidChangeTreeData: vscode.EventEmitter<RobotEntry | null> = new vscode.EventEmitter<RobotEntry | null>();
    readonly onDidChangeTreeData: vscode.Event<RobotEntry | null> = this._onDidChangeTreeData.event;

    fireRootChange() {
        this._onDidChangeTreeData.fire(null);
    }

    async getChildren(element?: RobotEntry): Promise<RobotEntry[]> {
        if (element) {
            // Get child elements.
            if (element.type == RobotEntryType.Task) {
                return []; // Tasks don't have children.
            }
            let yamlContents = element.robot.yamlContents;
            if (!yamlContents) {
                return [];
            }

            let tasks: object[] = yamlContents["tasks"];
            if (!tasks) {
                return [];
            }
            const robotInfo = element.robot;
            return Object.keys(tasks).map((task: string) => ({
                "label": task,
                "uri": vscode.Uri.file(robotInfo.filePath),
                "robot": robotInfo,
                "taskName": task,
                "iconPath": "symbol-misc",
                "type": RobotEntryType.Task,
            }));
        }

        if (!_globalSentMetric) {
            _globalSentMetric = true;
            vscode.commands.executeCommand(roboCommands.ROBOCORP_SEND_METRIC, {
                "name": "vscode.treeview.used",
                "value": "1",
            });
        }

        // Get root elements.
        let actionResult: ActionResult = await vscode.commands.executeCommand(
            roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
        );
        if (!actionResult.success) {
            OUTPUT_CHANNEL.appendLine(actionResult.message);
            return [];
        }
        let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

        if (!robotsInfo || robotsInfo.length == 0) {
            return [];
        }

        return robotsInfo.map((robotInfo: LocalRobotMetadataInfo) => ({
            "label": getRobotLabel(robotInfo),
            "uri": vscode.Uri.file(robotInfo.filePath),
            "robot": robotInfo,
            "iconPath": "package",
            "type": RobotEntryType.Robot,
        }));
    }

    getTreeItem(element: RobotEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(
            element.label,
            element.taskName ? vscode.TreeItemCollapsibleState.None : vscode.TreeItemCollapsibleState.Collapsed
        );
        treeItem.iconPath = new vscode.ThemeIcon(element.iconPath);
        return treeItem;
    }
}

export class LocatorsTreeDataProvider implements vscode.TreeDataProvider<LocatorEntry> {
    private _onDidChangeTreeData: vscode.EventEmitter<LocatorEntry | null> =
        new vscode.EventEmitter<LocatorEntry | null>();
    readonly onDidChangeTreeData: vscode.Event<LocatorEntry | null> = this._onDidChangeTreeData.event;

    private lastRobotEntry: RobotEntry = undefined;

    fireRootChange() {
        this._onDidChangeTreeData.fire(null);
    }

    onRobotsTreeSelectionChanged() {
        let robotEntry: RobotEntry = getSelectedRobot();
        if (!this.lastRobotEntry && !robotEntry) {
            // nothing changed
            return;
        }

        if (!this.lastRobotEntry && robotEntry) {
            // i.e.: we didn't have a selection previously: refresh.
            this.fireRootChange();
            return;
        }
        if (!robotEntry && this.lastRobotEntry) {
            this.fireRootChange();
            return;
        }
        if (robotEntry.robot.filePath != this.lastRobotEntry.robot.filePath) {
            // i.e.: the selection changed: refresh.
            this.fireRootChange();
            return;
        }
    }

    async getChildren(element?: LocatorEntry): Promise<LocatorEntry[]> {
        // i.e.: the contents of this tree depend on what's selected in the robots tree.
        const robotsTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
        if (!robotsTree || robotsTree.selection.length == 0) {
            this.lastRobotEntry = undefined;
            return [
                {
                    name: "<Waiting for Robot Selection...>",
                    type: "info",
                    line: 0,
                    column: 0,
                    filePath: undefined,
                },
            ];
        }
        let robotEntry: RobotEntry = robotsTree.selection[0];
        let actionResult: ActionResult = await vscode.commands.executeCommand(
            roboCommands.ROBOCORP_GET_LOCATORS_JSON_INFO,
            { "robotYaml": robotEntry.robot.filePath }
        );
        if (!actionResult["success"]) {
            this.lastRobotEntry = undefined;
            return [
                {
                    name: actionResult.message,
                    type: "error",
                    line: 0,
                    column: 0,
                    filePath: robotEntry.robot.filePath,
                },
            ];
        }

        this.lastRobotEntry = robotEntry;
        return actionResult["result"];
    }

    getTreeItem(element: LocatorEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(element.name);

        // https://microsoft.github.io/vscode-codicons/dist/codicon.html
        let iconPath = "file-media";
        if (element.type === "browser") {
            iconPath = "browser";
        } else if (element.type === "error") {
            iconPath = "error";
        }
        // Only add context to actual locator items
        if (element.type !== "error") treeItem.contextValue = "locatorEntry";
        treeItem.iconPath = new vscode.ThemeIcon(iconPath);
        return treeItem;
    }
}

export function refreshCloudTreeView() {
    let dataProvider: CloudTreeDataProvider = <CloudTreeDataProvider>(
        treeViewIdToTreeDataProvider.get(TREE_VIEW_ROBOCORP_CLOUD_TREE)
    );
    if (dataProvider) {
        dataProvider.refreshOnce = true;
        dataProvider.fireRootChange();
    }
}

export function refreshTreeView(treeViewId: string) {
    let dataProvider: RobotsTreeDataProvider = <RobotsTreeDataProvider>treeViewIdToTreeDataProvider.get(treeViewId);
    if (dataProvider) {
        dataProvider.fireRootChange();
    }
}

export function openRobotTreeSelection() {
    let robot: RobotEntry = getSelectedRobot();
    if (robot) {
        vscode.window.showTextDocument(robot.uri);
    }
}

export function cloudUploadRobotTreeSelection() {
    let robot: RobotEntry = getSelectedRobot();
    if (robot) {
        uploadRobot(robot.robot);
    }
}

export async function createRccTerminalTreeSelection() {
    let robot: RobotEntry = getSelectedRobot();
    if (robot) {
        createRccTerminal(robot.robot);
    }
}

export function runSelectedRobot(noDebug: boolean) {
    let element: RobotEntry = getSelectedRobot(
        "Unable to make launch (Robot task not selected in Robots Tree).",
        "Unable to make launch -- only 1 task must be selected."
    );
    runRobotRCC(noDebug, element.robot.filePath, element.taskName);
}

export function registerViews(context: ExtensionContext) {
    let cloudTreeDataProvider = new CloudTreeDataProvider();
    let cloudTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_CLOUD_TREE, {
        "treeDataProvider": cloudTreeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_CLOUD_TREE, cloudTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_CLOUD_TREE, cloudTreeDataProvider);

    let treeDataProvider = new RobotsTreeDataProvider();
    let robotsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE, {
        "treeDataProvider": treeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, robotsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, treeDataProvider);

    let robotContentTreeDataProvider = new RobotContentTreeDataProvider();
    let robotContentTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE, {
        "treeDataProvider": robotContentTreeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE, robotContentTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE, robotContentTreeDataProvider);
    context.subscriptions.push(
        robotsTree.onDidChangeSelection((e) => robotContentTreeDataProvider.onRobotsTreeSelectionChanged())
    );
    context.subscriptions.push(
        robotContentTree.onDidChangeSelection(async function () {
            await robotContentTreeDataProvider.onTreeSelectionChanged(robotContentTree);
        })
    );

    context.subscriptions.push(
        robotsTree.onDidChangeSelection((e) => {
            let events: RobotEntry[] = e.selection;
            if (!events || events.length == 0 || events.length > 1) {
                vscode.commands.executeCommand("setContext", "robocorp-code:single-task-selected", false);
                vscode.commands.executeCommand("setContext", "robocorp-code:single-robot-selected", false);
                return;
            }
            let robotEntry: RobotEntry = events[0];
            vscode.commands.executeCommand(
                "setContext",
                "robocorp-code:single-task-selected",
                robotEntry.type == RobotEntryType.Task
            );
            vscode.commands.executeCommand("setContext", "robocorp-code:single-robot-selected", true);
        })
    );

    let locatorsDataProvider = new LocatorsTreeDataProvider();
    let locatorsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_LOCATORS_TREE, {
        "treeDataProvider": locatorsDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_LOCATORS_TREE, locatorsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_LOCATORS_TREE, locatorsDataProvider);

    context.subscriptions.push(
        robotsTree.onDidChangeSelection((e) => locatorsDataProvider.onRobotsTreeSelectionChanged())
    );

    // Work items tree data provider definition
    /*
    const workItemsTreeDataProvider = new WorkItemsTreeDataProvider();
    const workItemsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE, {
        "treeDataProvider": workItemsTreeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE, workItemsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE, workItemsTreeDataProvider);
    context.subscriptions.push(
        robotsTree.onDidChangeSelection((e) => workItemsTreeDataProvider.onRobotsTreeSelectionChanged())
    );
    context.subscriptions.push(
        workItemsTree.onDidChangeSelection(async function () {
            await workItemsTreeDataProvider.onTreeSelectionChanged(workItemsTree);
        })
    );
    */

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
        refreshTreeView(TREE_VIEW_ROBOCORP_LOCATORS_TREE);
    }, 300);

    locatorsWatcher.onDidChange(onChangeLocatorsJson);
    locatorsWatcher.onDidCreate(onChangeLocatorsJson);
    locatorsWatcher.onDidDelete(onChangeLocatorsJson);

    context.subscriptions.push(robotsTree);
    context.subscriptions.push(locatorsTree);
    context.subscriptions.push(robotsWatcher);
    context.subscriptions.push(locatorsWatcher);
}
