import { TREE_VIEW_ROBOCORP_ROBOTS_TREE } from './robocorpViews';
import * as vscode from 'vscode';
import * as roboCommands from './robocorpCommands';
import { ExtensionContext } from 'vscode';
import { OUTPUT_CHANNEL } from './channel';
import { runRobotRCC } from './activities';


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

let treeViewIdToTreeView: Map<string, vscode.TreeView<any>> = new Map();
let treeViewIdToTreeDataProvider: Map<string, vscode.TreeDataProvider<any>> = new Map();

export function refreshTreeView(treeViewId: string) {
    let dataProvider: RobotsTreeDataProvider = <RobotsTreeDataProvider>treeViewIdToTreeDataProvider.get(treeViewId);
    if (dataProvider) {
        dataProvider.fireRootChange();
    }
}

export function runSelectedRobot(noDebug: boolean) {
    const tree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
    if (!tree || tree.selection.length == 0) {
        vscode.window.showWarningMessage("Unable to make launch (Robot task not selected in tree).");
        return;
    }

    if (tree.selection.length > 1) {
        vscode.window.showWarningMessage("Unable to make launch -- only 1 task must be selected.");
        return;
    }

    let element: RobotEntry = tree.selection[0];
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
    let tree = vscode.window.createTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE, { 'treeDataProvider': treeDataProvider });


    context.subscriptions.push(tree.onDidChangeSelection(e => {
        let events: RobotEntry[] = e.selection;
        if (!events || events.length == 0 || events.length > 1) {
            vscode.commands.executeCommand('setContext', 'robocorp-code:single-task-selected', false);
            return;
        }
        let robotEntry: RobotEntry = events[0]
        vscode.commands.executeCommand('setContext', 'robocorp-code:single-task-selected', robotEntry.type == RobotEntryType.Task);
    }));


    treeViewIdToTreeView.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, tree);
    treeViewIdToTreeDataProvider.set(TREE_VIEW_ROBOCORP_ROBOTS_TREE, treeDataProvider);

    let watcher: vscode.FileSystemWatcher = vscode.workspace.createFileSystemWatcher("**/*robot.yaml");

    let onChange = debounce(() => {
        // Note: this doesn't currently work if the parent folder is renamed or removed.
        // (https://github.com/microsoft/vscode/pull/110858)
        refreshTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
    }, 300);

    watcher.onDidChange(onChange);
    watcher.onDidCreate(onChange);
    watcher.onDidDelete(onChange);

    context.subscriptions.push(tree);
    context.subscriptions.push(watcher);
}