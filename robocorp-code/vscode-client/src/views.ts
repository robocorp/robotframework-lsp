import { TREE_VIEW_ROBOCORP_ROBOTS_TREE } from './robocorpViews';
import * as vscode from 'vscode';
import * as roboCommands from './robocorpCommands';
import { ExtensionContext } from 'vscode';


interface RobotEntry {
    label: string;
    uri: vscode.Uri;
    robot: LocalRobotMetadataInfo;
    taskName?: string;
    iconPath: string;
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

    private _onDidChangeFile: vscode.EventEmitter<vscode.FileChangeEvent[]>;

    constructor() {
        this._onDidChangeFile = new vscode.EventEmitter<vscode.FileChangeEvent[]>();
    }

    get onDidChangeFile(): vscode.Event<vscode.FileChangeEvent[]> {
        return this._onDidChangeFile.event;
    }

    // watch(uri: vscode.Uri, options: { recursive: boolean; excludes: string[]; }): vscode.Disposable {
    //     const watcher = fs.watch(uri.fsPath, { recursive: options.recursive }, async (event: string, filename: string | Buffer) => {
    //         const filepath = path.join(uri.fsPath, _.normalizeNFC(filename.toString()));

    //         // TODO support excludes (using minimatch library?)

    //         this._onDidChangeFile.fire([{
    //             type: event === 'change' ? vscode.FileChangeType.Changed : await _.exists(filepath) ? vscode.FileChangeType.Created : vscode.FileChangeType.Deleted,
    //             uri: uri.with({ path: filepath })
    //         } as vscode.FileChangeEvent]);
    //     });

    //     return { dispose: () => watcher.close() };
    // }

    // tree data provider

    async getChildren(element?: RobotEntry): Promise<RobotEntry[]> {
        if (element) {
            if (element.taskName) {
                return [];
            }
            let yamlContents = element.robot.yamlContents;
            if (yamlContents) {
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
                    }
                ));
            }
        }

        // Get root elements.
        let actionResult: ActionResult = await vscode.commands.executeCommand(
            roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
        );
        if (!actionResult.success) {
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
            }
        ));
    }

    getTreeItem(element: RobotEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(element.label, element.taskName ? vscode.TreeItemCollapsibleState.None : vscode.TreeItemCollapsibleState.Collapsed);
        treeItem.iconPath = new vscode.ThemeIcon(element.iconPath);
        return treeItem;
    }
}


export function registerViews(context: ExtensionContext) {
    context.subscriptions.push(vscode.window.createTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE, {
        treeDataProvider: new RobotsTreeDataProvider()
    }));
}