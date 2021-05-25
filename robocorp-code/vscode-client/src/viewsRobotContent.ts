import * as vscode from 'vscode';
import * as fs from 'fs';
import { OUTPUT_CHANNEL } from './channel';
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE, TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE } from './robocorpViews';
import { FSEntry, getSelectedRobot, RobotEntry, treeViewIdToTreeView } from './viewsCommon';
import { dirname, join } from 'path';
import { Uri } from 'vscode';
import { TreeItemCollapsibleState } from 'vscode';

const fsPromises = fs.promises;


export class RobotContentTreeDataProvider implements vscode.TreeDataProvider<FSEntry> {

    private _onDidChangeTreeData: vscode.EventEmitter<FSEntry | null> = new vscode.EventEmitter<FSEntry | null>();
    readonly onDidChangeTreeData: vscode.Event<FSEntry | null> = this._onDidChangeTreeData.event;

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

    async getChildren(element?: FSEntry): Promise<FSEntry[]> {
        let ret: FSEntry[] = [];
        if (!element) {
            // i.e.: the contents of this tree depend on what's selected in the robots tree.
            const robotsTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
            if (!robotsTree || robotsTree.selection.length == 0) {
                this.lastRobotEntry = undefined;
                return [{
                    name: "<Waiting for Robot Selection...>",
                    isDirectory: false,
                    filePath: undefined,
                }];
            }
            let robotEntry: RobotEntry = robotsTree.selection[0];
            this.lastRobotEntry = robotEntry;

            let robotUri = robotEntry.uri;
            try {
                let robotDir = dirname(robotUri.fsPath)
                let dirContents = await fsPromises.readdir(robotDir, { withFileTypes: true });
                for (const dirContent of dirContents) {
                    ret.push({
                        name: dirContent.name,
                        isDirectory: dirContent.isDirectory(),
                        filePath: join(robotDir, dirContent.name),
                    })
                }
            } catch (err) {
                OUTPUT_CHANNEL.appendLine('Error listing dir contents: ' + robotUri);
            }
            return ret;
        } else {
            // We have a parent...
            if (!element.isDirectory) {
                return ret;
            }
            try {
                let dirContents = await fsPromises.readdir(element.filePath, { withFileTypes: true });
                for (const dirContent of dirContents) {
                    ret.push({
                        name: dirContent.name,
                        isDirectory: dirContent.isDirectory(),
                        filePath: join(element.filePath, dirContent.name),
                    })
                }
            } catch (err) {
                OUTPUT_CHANNEL.appendLine('Error listing dir contents: ' + element.filePath);
            }
            return ret;
        }
    }

    getTreeItem(element: FSEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(element.name);
        if (element.isDirectory) {
            treeItem.collapsibleState = TreeItemCollapsibleState.Collapsed;
        } else {
            treeItem.collapsibleState = TreeItemCollapsibleState.None;
        }

        if (element.filePath === undefined) {
            // https://microsoft.github.io/vscode-codicons/dist/codicon.html
            treeItem.iconPath = new vscode.ThemeIcon("error");
        } else if (element.isDirectory) {
            treeItem.iconPath = vscode.ThemeIcon.Folder;
            treeItem.resourceUri = Uri.file(element.filePath);
        } else {
            treeItem.iconPath = vscode.ThemeIcon.File;
            treeItem.resourceUri = Uri.file(element.filePath);
        }
        return treeItem;
    }
}
