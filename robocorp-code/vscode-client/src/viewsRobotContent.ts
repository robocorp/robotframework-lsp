import * as vscode from "vscode";
import * as fs from "fs";
import { logError } from "./channel";
import { TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE } from "./robocorpViews";
import { FSEntry, getSelectedRobot, RobotEntry, treeViewIdToTreeView } from "./viewsCommon";
import { basename, dirname, join } from "path";
import { Uri } from "vscode";
import { RobotSelectionTreeDataProviderBase } from "./viewsRobotSelectionTreeBase";

const fsPromises = fs.promises;

export async function getCurrRobotTreeContentDir(): Promise<FSEntry | undefined> {
    let robotContentTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE);
    if (!robotContentTree) {
        return undefined;
    }

    let parentEntry: FSEntry | undefined = undefined;
    let selection: readonly FSEntry[] = robotContentTree.selection;
    if (selection.length > 0) {
        parentEntry = selection[0];
        if (!parentEntry.filePath) {
            parentEntry = undefined;
        }
    }
    if (!parentEntry) {
        let robot: RobotEntry | undefined = getSelectedRobot();
        if (!robot) {
            await vscode.window.showInformationMessage("Unable to create file in Robot (Robot not selected).");
            return undefined;
        }
        parentEntry = {
            filePath: dirname(robot.uri.fsPath),
            isDirectory: true,
            name: basename(robot.uri.fsPath),
        };
    }

    if (!parentEntry.isDirectory) {
        parentEntry = {
            filePath: dirname(parentEntry.filePath),
            isDirectory: true,
            name: basename(parentEntry.filePath),
        };
    }

    return parentEntry;
}

export async function newFileInRobotContentTree() {
    let currTreeDir: FSEntry | undefined = await getCurrRobotTreeContentDir();
    if (!currTreeDir) {
        return;
    }
    let filename: string = await vscode.window.showInputBox({
        "prompt": "Please provide file name. Current dir: " + currTreeDir.filePath,
        "ignoreFocusOut": true,
    });
    if (!filename) {
        return;
    }
    let targetFile = join(currTreeDir.filePath, filename);
    try {
        await vscode.workspace.fs.writeFile(Uri.file(targetFile), new Uint8Array());
    } catch (err) {
        logError("Unable to create file.", err, "VIEWS_NEW_FILE_IN_TREE");
        vscode.window.showErrorMessage("Unable to create file. Error: " + err.message);
    }
}

export async function renameResourceInRobotContentTree() {
    let robotContentTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE);
    if (!robotContentTree) {
        return undefined;
    }

    let selection: readonly FSEntry[] = robotContentTree.selection;
    if (!selection) {
        await vscode.window.showInformationMessage("No resources selected for rename.");
        return;
    }
    if (selection.length != 1) {
        await vscode.window.showInformationMessage("Please select a single resource for rename.");
        return;
    }

    let entry = selection[0];
    let uri = Uri.file(entry.filePath);
    let stat;
    try {
        stat = await vscode.workspace.fs.stat(uri);
    } catch (err) {
        // unable to get stat (file may have been removed in the meanwhile).
        await vscode.window.showErrorMessage("Unable to stat resource during rename.");
    }
    if (stat) {
        try {
            let newName: string = await vscode.window.showInputBox({
                "prompt":
                    "Please provide new name for: " +
                    basename(entry.filePath) +
                    " (at: " +
                    dirname(entry.filePath) +
                    ")",
                "ignoreFocusOut": true,
            });
            if (!newName) {
                return;
            }
            let target = Uri.file(join(dirname(entry.filePath), newName));
            await vscode.workspace.fs.rename(uri, target, { overwrite: false });
        } catch (err) {
            logError("Error renaming resource: " + entry.filePath, err, "VIEWS_RENAME_RESOURCE");
            let msg = await vscode.window.showErrorMessage("Error renaming resource: " + entry.filePath);
        }
    }
}

export async function deleteResourceInRobotContentTree() {
    let robotContentTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE);
    if (!robotContentTree) {
        return undefined;
    }

    let selection: readonly FSEntry[] = robotContentTree.selection;
    if (!selection) {
        await vscode.window.showInformationMessage("No resources selected for deletion.");
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
                let msg = await vscode.window.showErrorMessage(
                    "Unable to move to trash: " + entry.filePath + ". How to proceed?",
                    "Delete permanently",
                    "Cancel"
                );
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
        "prompt": "Please provide dir name. Current dir: " + currTreeDir.filePath,
        "ignoreFocusOut": true,
    });
    if (!directoryName) {
        return;
    }
    let targetFile = join(currTreeDir.filePath, directoryName);
    try {
        await vscode.workspace.fs.createDirectory(Uri.file(targetFile));
    } catch (err) {
        logError("Unable to create directory: " + targetFile, err, "VIEWS_NEW_FOLDER");
        vscode.window.showErrorMessage("Unable to create directory. Error: " + err.message);
    }
}

export class RobotContentTreeDataProvider extends RobotSelectionTreeDataProviderBase {
    private _onForceSelectionFromTreeData: vscode.EventEmitter<RobotEntry[]> = new vscode.EventEmitter<RobotEntry[]>();
    readonly onForceSelectionFromTreeData: vscode.Event<RobotEntry[]> = this._onForceSelectionFromTreeData.event;

    async getChildren(element?: FSEntry): Promise<FSEntry[]> {
        let ret: FSEntry[] = [];
        if (!element) {
            // i.e.: the contents of this tree depend on what's selected in the robots tree.
            const robotEntry: RobotEntry = getSelectedRobot();
            if (!robotEntry) {
                this.lastRobotEntry = undefined;
                return [
                    {
                        name: "<Waiting for Robot Selection...>",
                        isDirectory: false,
                        filePath: undefined,
                    },
                ];
            }
            this.lastRobotEntry = robotEntry;

            let robotUri = robotEntry.uri;
            try {
                let robotDir = dirname(robotUri.fsPath);
                let dirContents = await fsPromises.readdir(robotDir, { withFileTypes: true });
                sortDirContents(dirContents);
                for (const dirContent of dirContents) {
                    ret.push({
                        name: dirContent.name,
                        isDirectory: dirContent.isDirectory(),
                        filePath: join(robotDir, dirContent.name),
                    });
                }
            } catch (err) {
                // i.e.: this means that the selection is now invalid (directory was deleted).
                setTimeout(() => {
                    this._onForceSelectionFromTreeData.fire(undefined);
                }, 50);
            }
            return ret;
        } else {
            // We have a parent...
            if (!element.isDirectory) {
                return ret;
            }
            try {
                let dirContents = await fsPromises.readdir(element.filePath, { withFileTypes: true });
                sortDirContents(dirContents);
                for (const dirContent of dirContents) {
                    ret.push({
                        name: dirContent.name,
                        isDirectory: dirContent.isDirectory(),
                        filePath: join(element.filePath, dirContent.name),
                    });
                }
            } catch (err) {
                logError("Error listing dir contents: " + element.filePath, err, "VIEWS_LIST_CHILDREN");
            }
            return ret;
        }
    }
}

function sortDirContents(dirContents: fs.Dirent[]) {
    dirContents.sort((entry1, entry2) => {
        if (entry1.isDirectory() != entry2.isDirectory()) {
            if (entry1.isDirectory()) {
                return -1;
            }
            if (entry2.isDirectory()) {
                return 1;
            }
        }

        return entry1.name.toLowerCase().localeCompare(entry2.name.toLowerCase());
    });
}
