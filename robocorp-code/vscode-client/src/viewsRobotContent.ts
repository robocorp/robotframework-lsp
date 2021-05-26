import * as vscode from 'vscode';
import * as fs from 'fs';
import { OUTPUT_CHANNEL } from './channel';
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE, TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE } from './robocorpViews';
import { FSEntry, getSelectedRobot, RobotEntry, treeViewIdToTreeDataProvider, treeViewIdToTreeView } from './viewsCommon';
import { basename, dirname, join } from 'path';
import { Uri } from 'vscode';
import { TreeItemCollapsibleState } from 'vscode';

const fsPromises = fs.promises;

export async function getCurrRobotTreeContentDir(): Promise<FSEntry | undefined> {
    let robotContentTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE);
    if (!robotContentTree) {
        return undefined;
    }

    let parentEntry: FSEntry | undefined = undefined;
    let selection: FSEntry[] = robotContentTree.selection;
    if (selection.length > 0) {
        parentEntry = selection[0];
        if (!parentEntry.filePath) {
            parentEntry = undefined;
        }
    }
    if (!parentEntry) {
        let robot: RobotEntry | undefined = getSelectedRobot();
        if (!robot) {
            await vscode.window.showInformationMessage('Unable to create file in Robot (Robot not selected).')
            return undefined;
        }
        parentEntry = {
            filePath: dirname(robot.uri.fsPath),
            isDirectory: true,
            name: basename(robot.uri.fsPath)
        }
    }

    if (!parentEntry.isDirectory) {
        parentEntry = {
            filePath: dirname(parentEntry.filePath),
            isDirectory: true,
            name: basename(parentEntry.filePath)
        }
    }

    return parentEntry;
}

export async function newFileInRobotContentTree() {
    let currTreeDir: FSEntry | undefined = await getCurrRobotTreeContentDir();
    if (!currTreeDir) {
        return;
    }
    let filename: string = await vscode.window.showInputBox({
        'prompt': 'Please provide file name. Current dir: ' + currTreeDir.filePath,
        'ignoreFocusOut': true,
    });
    if (!filename) {
        return;
    }
    let targetFile = join(currTreeDir.filePath, filename);
    try {
        await vscode.workspace.fs.writeFile(Uri.file(targetFile), new Uint8Array());
    } catch (err) {
        vscode.window.showErrorMessage('Unable to create file. Error: ' + err);
    }
}

export async function deleteResourceInRobotContentTree() {
    let robotContentTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE);
    if (!robotContentTree) {
        return undefined;
    }

    let selection: FSEntry[] = robotContentTree.selection;
    if (!selection) {
        await vscode.window.showInformationMessage("No resources selected for deletion.")
        return;
    }

    for (const entry of selection) {
        let uri = Uri.file(entry.filePath);
        let stat;
        try {
            stat = await vscode.workspace.fs.stat(uri);
        } catch (err) {
            // unable to get stat (file may have been removed in the meanwhile).
        }
        if (stat) {
            try {
                await vscode.workspace.fs.delete(uri, { recursive: true, useTrash: true });
            } catch (err) {
                let msg = await vscode.window.showErrorMessage("Unable to move to trash: " + entry.filePath + ". How to proceed?", "Delete permanently", "Cancel")
                if (msg == "Delete permanently") {
                    await vscode.workspace.fs.delete(uri, { recursive: true, useTrash: false });
                } else {
                    return;
                }
            }
        }
    }
}

export async function newFolderInRobotContentTree() {
    let currTreeDir: FSEntry | undefined = await getCurrRobotTreeContentDir();
    if (!currTreeDir) {
        return;
    }
    let directoryName: string = await vscode.window.showInputBox({
        'prompt': 'Please provide dir name. Current dir: ' + currTreeDir.filePath,
        'ignoreFocusOut': true,
    });
    if (!directoryName) {
        return;
    }
    let targetFile = join(currTreeDir.filePath, directoryName);
    try {
        await vscode.workspace.fs.createDirectory(Uri.file(targetFile));
    } catch (err) {
        vscode.window.showErrorMessage('Unable to create directory. Error: ' + err);
    }
}

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
