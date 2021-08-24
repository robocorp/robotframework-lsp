import { TREE_VIEW_ROBOCORP_CLOUD_TREE, TREE_VIEW_ROBOCORP_LOCATORS_TREE, TREE_VIEW_ROBOCORP_ROBOTS_TREE, TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE } from './robocorpViews';
import * as vscode from 'vscode';
import * as roboCommands from './robocorpCommands';
import { ExtensionContext } from 'vscode';
import { OUTPUT_CHANNEL } from './channel';
import { runRobotRCC, uploadRobot } from './activities';
import { createRccTerminal } from './rccTerminal';
import { RobotContentTreeDataProvider } from './viewsRobotContent';
import { basename, CloudEntry, debounce, getSelectedLocator, getSelectedRobot, LocatorEntry, RobotEntry, RobotEntryType, treeViewIdToTreeDataProvider, treeViewIdToTreeView } from './viewsCommon';


function getRobotLabel(robotInfo: LocalRobotMetadataInfo): string {
    let label: string = undefined;
    if (robotInfo.yamlContents) {
        label = robotInfo.yamlContents['name'];
    }
    if (!label) {
        if (robotInfo.directory) {
            label = basename(robotInfo.directory)
        }
    }
    if (!label) {
        label = '';
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
            let accountInfoResult: ActionResult = await vscode.commands.executeCommand(roboCommands.ROBOCORP_GET_LINKED_ACCOUNT_INFO_INTERNAL);
            if (!accountInfoResult.success) {
                return [{
                    'label': 'Account not linked. Click to link account.',
                    'iconPath': 'link',
                    'command': {
                        'title': 'Link to Robocorp Cloud',
                        'command': roboCommands.ROBOCORP_CLOUD_LOGIN,
                    }
                }];
            }
            let accountInfo = accountInfoResult.result;
            let ret: CloudEntry[] = [{
                'label': 'Account: ' + accountInfo['fullname'] + ' (' + accountInfo['email'] + ')',
            }];


            let refresh: boolean = this.refreshOnce;
            this.refreshOnce = false;
            let actionResult: ListWorkspacesActionResult = await vscode.commands.executeCommand(
                roboCommands.ROBOCORP_CLOUD_LIST_WORKSPACES_INTERNAL, { 'refresh': refresh }
            );
            if (actionResult.success) {
                let workspaceInfo: WorkspaceInfo[] = actionResult.result;
                for (let i = 0; i < workspaceInfo.length; i++) {
                    const element = workspaceInfo[i];
                    let children: CloudEntry[] = [];

                    let packages: PackageInfo[] = element.packages;
                    for (let j = 0; j < packages.length; j++) {
                        const p = packages[j];
                        children.push({ 'label': p.name });
                    }

                    ret.push({
                        'label': element.workspaceName,
                        'children': children
                    });
                }
            }

            return ret;
        }
        if (element.children) {
            return element.children;
        }
        return [];
    }

    getTreeItem(element: CloudEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(element.label, element.children ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None);
        treeItem.command = element.command;
        treeItem.iconPath = new vscode.ThemeIcon(element.iconPath);
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

            let tasks: object[] = yamlContents['tasks'];
            if (!tasks) {
                return [];
            }
            const robotInfo = element.robot;
            return Object.keys(tasks).map((task: string) => (
                {
                    'label': task,
                    'uri': vscode.Uri.file(robotInfo.filePath),
                    'robot': robotInfo,
                    'taskName': task,
                    'iconPath': 'symbol-misc',
                    'type': RobotEntryType.Task,
                }
            ));
        }

        if (!_globalSentMetric) {
            _globalSentMetric = true;
            vscode.commands.executeCommand(roboCommands.ROBOCORP_SEND_METRIC, {
                'name': 'vscode.treeview.used', 'value': '1'
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

        return robotsInfo.map((robotInfo: LocalRobotMetadataInfo) => (
            {
                'label': getRobotLabel(robotInfo),
                'uri': vscode.Uri.file(robotInfo.filePath),
                'robot': robotInfo,
                'iconPath': 'package',
                'type': RobotEntryType.Robot,
            }
        ));
    }

    getTreeItem(element: RobotEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(element.label, element.taskName ? vscode.TreeItemCollapsibleState.None : vscode.TreeItemCollapsibleState.Collapsed);
        treeItem.iconPath = new vscode.ThemeIcon(element.iconPath);
        return treeItem;
    }
}


export class LocatorsTreeDataProvider implements vscode.TreeDataProvider<LocatorEntry> {

    private _onDidChangeTreeData: vscode.EventEmitter<LocatorEntry | null> = new vscode.EventEmitter<LocatorEntry | null>();
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
            return [{
                name: "<Waiting for Robot Selection...>",
                type: "info",
                line: 0,
                column: 0,
                filePath: undefined,
            }];
        }
        let robotEntry: RobotEntry = robotsTree.selection[0];
        let actionResult: ActionResult = await vscode.commands.executeCommand(
            roboCommands.ROBOCORP_GET_LOCATORS_JSON_INFO, { 'robotYaml': robotEntry.robot.filePath });
        if (!actionResult['success']) {
            this.lastRobotEntry = undefined;
            return [{
                name: actionResult.message,
                type: "error",
                line: 0,
                column: 0,
                filePath: robotEntry.robot.filePath,
            }];
        }

        this.lastRobotEntry = robotEntry;
        let locatorInfo: LocatorEntry[] = actionResult['result'];
        return locatorInfo;
    }

    getTreeItem(element: LocatorEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(element.name);

        // https://microsoft.github.io/vscode-codicons/dist/codicon.html
        let iconPath = "file-media";
        if (element.type == "browser") {
            iconPath = "browser";
        } else if (element.type == "error") {
            iconPath = "error";

        }
        treeItem.iconPath = new vscode.ThemeIcon(iconPath);
        treeItem.contextValue = "locatorEntry";
        return treeItem;
    }
}

export function refreshCloudTreeView() {
    let dataProvider: CloudTreeDataProvider = <CloudTreeDataProvider>treeViewIdToTreeDataProvider.get(TREE_VIEW_ROBOCORP_CLOUD_TREE);
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
    let cloudTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_CLOUD_TREE, { 'treeDataProvider': cloudTreeDataProvider });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_CLOUD_TREE, cloudTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_CLOUD_TREE, cloudTreeDataProvider);

    let treeDataProvider = new RobotsTreeDataProvider();
    let robotsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE, { 'treeDataProvider': treeDataProvider });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, robotsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, treeDataProvider);

    let robotContentTreeDataProvider = new RobotContentTreeDataProvider();
    let robotContentTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE, { 'treeDataProvider': robotContentTreeDataProvider });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE, robotContentTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE, robotContentTreeDataProvider);
    context.subscriptions.push(robotsTree.onDidChangeSelection(
        e => robotContentTreeDataProvider.onRobotsTreeSelectionChanged()
    ));
    context.subscriptions.push(robotContentTree.onDidChangeSelection(
        async function () {
            await robotContentTreeDataProvider.onRobotContentTreeTreeSelectionChanged(robotContentTree);
        }
    ));

    context.subscriptions.push(robotsTree.onDidChangeSelection(e => {
        let events: RobotEntry[] = e.selection;
        if (!events || events.length == 0 || events.length > 1) {
            vscode.commands.executeCommand('setContext', 'robocorp-code:single-task-selected', false);
            vscode.commands.executeCommand('setContext', 'robocorp-code:single-robot-selected', false);
            return;
        }
        let robotEntry: RobotEntry = events[0]
        vscode.commands.executeCommand('setContext', 'robocorp-code:single-task-selected', robotEntry.type == RobotEntryType.Task);
        vscode.commands.executeCommand('setContext', 'robocorp-code:single-robot-selected', true);
    }));


    let locatorsDataProvider = new LocatorsTreeDataProvider();
    let locatorsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_LOCATORS_TREE, { 'treeDataProvider': locatorsDataProvider });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_LOCATORS_TREE, locatorsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_LOCATORS_TREE, locatorsDataProvider);

    context.subscriptions.push(robotsTree.onDidChangeSelection(
        e => locatorsDataProvider.onRobotsTreeSelectionChanged()
    ));

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