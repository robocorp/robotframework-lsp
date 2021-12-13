import {
    TREE_VIEW_ROBOCORP_CLOUD_TREE,
    TREE_VIEW_ROBOCORP_LOCATORS_TREE,
    TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE,
    TREE_VIEW_ROBOCORP_ROBOTS_TREE,
    TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE,
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
    onSelectedRobotChanged,
    RobotEntry,
    RobotEntryType,
    setSelectedRobot,
    treeViewIdToTreeDataProvider,
    treeViewIdToTreeView,
} from "./viewsCommon";
import { ROBOCORP_SUBMIT_ISSUE } from "./robocorpCommands";
import { RobotSelectionTreeDataProviderBase } from "./viewsRobotSelection";
import { uriExists } from "./files";

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
            let accountInfoResult: ActionResult<any> = await vscode.commands.executeCommand(
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

function empty<T>(array: T[]) {
    return array === undefined || array.length === 0;
}

export class RobotsTreeDataProvider implements vscode.TreeDataProvider<RobotEntry> {
    private _onDidChangeTreeData: vscode.EventEmitter<RobotEntry | null> = new vscode.EventEmitter<RobotEntry | null>();
    readonly onDidChangeTreeData: vscode.Event<RobotEntry | null> = this._onDidChangeTreeData.event;

    private _onForceSelectionFromTreeData: vscode.EventEmitter<RobotEntry[]> = new vscode.EventEmitter<RobotEntry[]>();
    readonly onForceSelectionFromTreeData: vscode.Event<RobotEntry[]> = this._onForceSelectionFromTreeData.event;

    private lastRoot: RobotEntry[] | undefined = undefined;

    fireRootChange() {
        this._onDidChangeTreeData.fire(null);
    }

    /**
     * Note that we make sure to only return valid entries here (i.e.: no entries
     * where RobotEntry.type === RobotEntryType.Error).
     */
    async getValidCachedOrComputeChildren(element?: RobotEntry): Promise<RobotEntry[]> {
        if (element === undefined) {
            if (this.lastRoot !== undefined) {
                let ret: RobotEntry[] = this.lastRoot.filter((e) => {
                    return e.type !== RobotEntryType.Error;
                });
                if (ret.length > 0) {
                    // We need to check whether entries still exist.
                    let foundAll: boolean = true;
                    for (const entry of ret) {
                        if (!(await uriExists(entry.uri))) {
                            foundAll = false;
                            break;
                        }
                    }
                    if (foundAll) {
                        return ret;
                    }
                }
            }
        }
        let ret: RobotEntry[] = await this.getChildren(element);
        // Remove any "error" entries
        return ret.filter((e) => {
            return e.type !== RobotEntryType.Error;
        });
    }

    /**
     * This function will compute the children and store the `lastRoot`
     * cache (if element === undefined).
     */
    async getChildren(element?: RobotEntry): Promise<RobotEntry[]> {
        let ret = await this.computeChildren(element);
        if (element === undefined) {
            // i.e.: this is the root entry, so, we've
            // collected the actual robots here.

            let notifySelection = false;
            if (empty(this.lastRoot) && empty(ret)) {
                // Don't notify of anything, nothing changed...
            } else if (empty(this.lastRoot)) {
                // We had nothing and now we have something, notify.
                if (!empty(ret)) {
                    notifySelection = true;
                }
            } else {
                // lastRoot is valid
                // We had something and now we have nothing, notify.
                if (empty(ret)) {
                    notifySelection = true;
                }
            }
            if (!empty(ret) && !notifySelection) {
                // Verify if the last selection is still valid (if it's not we need
                // to notify).
                let currentSelectedRobot = getSelectedRobot();
                let found = false;
                for (const entry of ret) {
                    if (currentSelectedRobot == entry) {
                        found = true;
                    }
                }
                if (!found) {
                    notifySelection = true;
                }
            }
            this.lastRoot = ret;

            if (notifySelection) {
                setTimeout(() => {
                    this._onForceSelectionFromTreeData.fire(this.lastRoot);
                }, 50);
            }

            if (ret.length === 0) {
                // No robot was actually found, so, we'll return a dummy entry
                // giving more instructions to the user.
                let added: boolean = false;
                for (const label of [
                    "No robots found.",
                    "To get started:",
                    "➔ Run the “Robocorp: Create Robot” action",
                    "➔ Open a robot folder (with a “robot.yaml” file)",
                    "➔ Open a parent folder (with multiple robots)",
                ]) {
                    ret.push({
                        "label": label,
                        "uri": undefined,
                        "robot": undefined,
                        "taskName": undefined,
                        "iconPath": added ? "" : "error",
                        "type": RobotEntryType.Error,
                        "parent": element,
                    });
                    added = true;
                }
            }
        }
        return ret;
    }

    async getParent?(element: RobotEntry): Promise<RobotEntry> {
        return element.parent;
    }

    async computeChildren(element?: RobotEntry): Promise<RobotEntry[]> {
        if (element) {
            if (element.type === RobotEntryType.Error) {
                return [];
            }

            // Get child elements.
            if (element.type === RobotEntryType.Task) {
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
                "parent": element,
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
        let actionResult: ActionResult<LocalRobotMetadataInfo[]> = await vscode.commands.executeCommand(
            roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
        );
        if (!actionResult.success) {
            OUTPUT_CHANNEL.appendLine(actionResult.message);
            return [];
        }
        let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

        if (empty(robotsInfo)) {
            return [];
        }

        return robotsInfo.map((robotInfo: LocalRobotMetadataInfo) => ({
            "label": getRobotLabel(robotInfo),
            "uri": vscode.Uri.file(robotInfo.filePath),
            "robot": robotInfo,
            "iconPath": "package",
            "type": RobotEntryType.Robot,
            "parent": element,
        }));
    }

    getTreeItem(element: RobotEntry): vscode.TreeItem {
        const isTask: boolean = element.type === RobotEntryType.Task;
        const treeItem = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.Collapsed);
        if (element.type === RobotEntryType.Robot) {
            treeItem.contextValue = "robotItem";
        } else if (isTask) {
            treeItem.contextValue = "taskItem";
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else if (element.type === RobotEntryType.Error) {
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        }
        if (element.iconPath) {
            treeItem.iconPath = new vscode.ThemeIcon(element.iconPath);
        }
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

    async onRobotsTreeSelectionChanged(robotEntry: RobotEntry | undefined) {
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
        const robotEntry: RobotEntry = getSelectedRobot();
        if (!robotEntry) {
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
        let actionResult: ActionResult<LocatorEntry[]> = await vscode.commands.executeCommand(
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
        if (element.type !== "error") {
            treeItem.contextValue = "locatorEntry";
        }
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
    selection: RobotEntry[]
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
    let cloudTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_CLOUD_TREE, {
        "treeDataProvider": cloudTreeDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_CLOUD_TREE, cloudTree);
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
        robotContentTree.onDidChangeSelection(async function () {
            await robotContentTreeDataProvider.onTreeSelectionChanged(robotContentTree);
        })
    );
    context.subscriptions.push(
        robotContentTreeDataProvider.onForceSelectionFromTreeData(
            async (e) => await onChangedRobotSelection(robotsTree, robotsTreeDataProvider, robotsTree.selection)
        )
    );

    // Locators
    let locatorsDataProvider = new LocatorsTreeDataProvider();
    let locatorsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_LOCATORS_TREE, {
        "treeDataProvider": locatorsDataProvider,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_LOCATORS_TREE, locatorsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_LOCATORS_TREE, locatorsDataProvider);

    context.subscriptions.push(onSelectedRobotChanged((e) => locatorsDataProvider.onRobotsTreeSelectionChanged(e)));

    // Work items tree data provider definition
    const workItemsTreeDataProvider = new WorkItemsTreeDataProvider();
    const workItemsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE, {
        "treeDataProvider": workItemsTreeDataProvider,
        "canSelectMany": true,
    });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE, workItemsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE, workItemsTreeDataProvider);
    context.subscriptions.push(
        onSelectedRobotChanged((e) => workItemsTreeDataProvider.onRobotsTreeSelectionChanged(e))
    );

    context.subscriptions.push(
        workItemsTree.onDidChangeSelection(async function () {
            await workItemsTreeDataProvider.onTreeSelectionChanged(workItemsTree);
        })
    );

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
