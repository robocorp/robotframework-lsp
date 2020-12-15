import { TREE_VIEW_ROBOCORP_LOCATORS_TREE, TREE_VIEW_ROBOCORP_ROBOTS_TREE } from './robocorpViews';
import * as vscode from 'vscode';
import * as roboCommands from './robocorpCommands';
import { ExtensionContext } from 'vscode';
import { OUTPUT_CHANNEL } from './channel';
import { runRobotRCC } from './activities';


interface LocatorEntry {
    name: string;
    line: number;
    column: number;
    type: string; // "browser", "image", "coordinate", ...
    filePath: string;
}

enum RobotEntryType {
    Robot,
    Task
}

interface RobotEntry {
    label: string;
    uri: vscode.Uri;
    robot: LocalRobotMetadataInfo;
    taskName?: string;
    iconPath: string;
    type: RobotEntryType;
}


function basename(s) {
    return s.split('\\').pop().split('/').pop();
}

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
        const robotsTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
        if (!robotsTree) {
            return;
        }
        let robotEntry: RobotEntry = undefined;
        if (robotsTree.selection.length != 0) {
            robotEntry = robotsTree.selection[0];
        }
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
            return [];
        }
        let robotEntry: RobotEntry = robotsTree.selection[0];
        let actionResult: ActionResult = await vscode.commands.executeCommand(
            roboCommands.ROBOCORP_GET_LOCATORS_JSON_INFO, { 'robotYaml': robotEntry.robot.filePath });
        if (!actionResult['success']) {
            this.lastRobotEntry = undefined;
            return [];
        }

        this.lastRobotEntry = robotEntry;
        let locatorInfo: LocatorEntry[] = actionResult['result'];
        return locatorInfo;
    }

    getTreeItem(element: LocatorEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(element.name);
        treeItem.iconPath = new vscode.ThemeIcon(element.type == "browser" ? "browser" : "file-media");
        return treeItem;
    }
}

let treeViewIdToTreeView: Map<string, vscode.TreeView<any>> = new Map();
let treeViewIdToTreeDataProvider: Map<string, vscode.TreeDataProvider<any>> = new Map();

export function refreshTreeView(treeViewId: string) {
    let dataProvider: RobotsTreeDataProvider = <RobotsTreeDataProvider>treeViewIdToTreeDataProvider.get(treeViewId);
    if (dataProvider) {
        dataProvider.fireRootChange();
    }
}

export function runSelectedRobot(noDebug: boolean) {
    const robotsTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
    if (!robotsTree || robotsTree.selection.length == 0) {
        vscode.window.showWarningMessage("Unable to make launch (Robot task not selected in robotsTree).");
        return;
    }

    if (robotsTree.selection.length > 1) {
        vscode.window.showWarningMessage("Unable to make launch -- only 1 task must be selected.");
        return;
    }

    let element: RobotEntry = robotsTree.selection[0];
    runRobotRCC(noDebug, element.robot.filePath, element.taskName);
}

const debounce = (func, wait) => {
    let timeout;

    return function wrapper(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };

        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

export function registerViews(context: ExtensionContext) {
    let treeDataProvider = new RobotsTreeDataProvider();
    let robotsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE, { 'treeDataProvider': treeDataProvider });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, robotsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, treeDataProvider);

    context.subscriptions.push(robotsTree.onDidChangeSelection(e => {
        let events: RobotEntry[] = e.selection;
        if (!events || events.length == 0 || events.length > 1) {
            vscode.commands.executeCommand('setContext', 'robocorp-code:single-task-selected', false);
            return;
        }
        let robotEntry: RobotEntry = events[0]
        vscode.commands.executeCommand('setContext', 'robocorp-code:single-task-selected', robotEntry.type == RobotEntryType.Task);
    }));


    let locatorsDataProvider = new LocatorsTreeDataProvider();
    let locatorsTree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_LOCATORS_TREE, { 'treeDataProvider': locatorsDataProvider });
    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_LOCATORS_TREE, locatorsTree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_LOCATORS_TREE, locatorsDataProvider);

    robotsTree.onDidChangeSelection(
        e => locatorsDataProvider.onRobotsTreeSelectionChanged()
    );

    let watcher: vscode.FileSystemWatcher = vscode.workspace.createFileSystemWatcher("**/*robot.yaml");

    let onChange = debounce(() => {
        // Note: this doesn't currently work if the parent folder is renamed or removed.
        // (https://github.com/microsoft/vscode/pull/110858)
        refreshTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
    }, 300);

    watcher.onDidChange(onChange);
    watcher.onDidCreate(onChange);
    watcher.onDidDelete(onChange);

    context.subscriptions.push(robotsTree);
    context.subscriptions.push(locatorsTree);
    context.subscriptions.push(watcher);
}