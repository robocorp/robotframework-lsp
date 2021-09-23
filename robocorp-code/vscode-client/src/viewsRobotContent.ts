import * as vscode from 'vscode';
import * as fs from 'fs';
import { logError } from './channel';
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE, TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE } from './robocorpViews';
import { debounce, FSEntry, getSelectedRobot, RobotEntry, treeViewIdToTreeDataProvider, treeViewIdToTreeView } from './viewsCommon';
import { basename, dirname, join, resolve } from 'path';
import { FileSystemWatcher, Uri, commands } from 'vscode';
import { TreeItemCollapsibleState } from 'vscode';
import { ROBOCORP_LIST_WORK_ITEMS_INTERNAL } from './robocorpCommands';

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
        logError('Unable to create file.', err);
        vscode.window.showErrorMessage('Unable to create file. Error: ' + err.message);
    }
}

export async function renameResourceInRobotContentTree() {
    let robotContentTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE);
    if (!robotContentTree) {
        return undefined;
    }

    let selection: FSEntry[] = robotContentTree.selection;
    if (!selection) {
        await vscode.window.showInformationMessage("No resources selected for rename.")
        return;
    }
    if (selection.length != 1) {
        await vscode.window.showInformationMessage("Please select a single resource for rename.")
        return;
    }

    let entry = selection[0];
    let uri = Uri.file(entry.filePath);
    let stat;
    try {
        stat = await vscode.workspace.fs.stat(uri);
    } catch (err) {
        // unable to get stat (file may have been removed in the meanwhile).
        await vscode.window.showErrorMessage("Unable to stat resource during rename.")
    }
    if (stat) {
        try {
            let newName: string = await vscode.window.showInputBox({
                'prompt': 'Please provide new name for: ' + basename(entry.filePath) + ' (at: ' + dirname(entry.filePath) + ')',
                'ignoreFocusOut': true,
            });
            if (!newName) {
                return;
            }
            let target = Uri.file(join(dirname(entry.filePath), newName));
            await vscode.workspace.fs.rename(uri, target, { overwrite: false });
        } catch (err) {
            logError("Error renaming resource: " + entry.filePath, err);
            let msg = await vscode.window.showErrorMessage("Error renaming resource: " + entry.filePath);
        }
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
        logError('Unable to create directory: ' + targetFile, err);
        vscode.window.showErrorMessage('Unable to create directory. Error: ' + err.message);
    }
}

export class RobotContentTreeDataProvider implements vscode.TreeDataProvider<FSEntry> {

    private _onDidChangeTreeData: vscode.EventEmitter<FSEntry | null> = new vscode.EventEmitter<FSEntry | null>();
    readonly onDidChangeTreeData: vscode.Event<FSEntry | null> = this._onDidChangeTreeData.event;

    protected lastRobotEntry: RobotEntry = undefined;
    private lastWatcher: FileSystemWatcher | undefined = undefined;

    fireRootChange() {
        this._onDidChangeTreeData.fire(null);
    }

    robotSelectionChanged(robotEntry: RobotEntry) {
        // When the robot selection changes, we need to start tracking file-changes at the proper place.
        if (this.lastWatcher) {
            this.lastWatcher.dispose();
            this.lastWatcher = undefined;
        }
        this.fireRootChange();

        let d = basename(dirname(robotEntry.uri.fsPath));
        let watcher: FileSystemWatcher = vscode.workspace.createFileSystemWatcher('**/' + d + '/**', false, true, false);
        this.lastWatcher = watcher;

        let onChangedSomething = debounce(() => {
            // Note: this doesn't currently work if the parent folder is renamed or removed.
            // (https://github.com/microsoft/vscode/pull/110858)
            this.fireRootChange();
        }, 100);

        watcher.onDidCreate(onChangedSomething);
        watcher.onDidDelete(onChangedSomething);
    }

    onRobotsTreeSelectionChanged() {
        let robotEntry: RobotEntry = getSelectedRobot();
        if (!this.lastRobotEntry && !robotEntry) {
            // nothing changed
            return;
        }

        if (!this.lastRobotEntry && robotEntry) {
            // i.e.: we didn't have a selection previously: refresh.
            this.robotSelectionChanged(robotEntry);
            return;
        }
        if (!robotEntry && this.lastRobotEntry) {
            this.robotSelectionChanged(robotEntry);
            return;
        }
        if (robotEntry.robot.filePath != this.lastRobotEntry.robot.filePath) {
            // i.e.: the selection changed: refresh.
            this.robotSelectionChanged(robotEntry);
            return;
        }

    }

    async onRobotContentTreeTreeSelectionChanged(robotContentTree: vscode.TreeView<FSEntry>) {
        let selection = robotContentTree.selection;
        if (selection.length == 1) {
            let entry: FSEntry = selection[0];
            if (entry.filePath && !entry.isDirectory) {
                let uri = Uri.file(entry.filePath);
                let document = await vscode.workspace.openTextDocument(uri);
                if (document) {
                    await vscode.window.showTextDocument(document);
                }
            }
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
                logError('Error listing dir contents: ' + robotUri, err);
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
                logError('Error listing dir contents: ' + element.filePath, err);
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

const WORK_ITEM_TEMPLATE = `[
    {
        "payload": {
           "message": "Hello World!"
        },
        "files": {
            "orders.xlsx": "orders.xlsx"
        }
    }
]`;

async function getWorkItemInfo(): Promise<WorkItemsInfo | null> {
    // Would there be a faster way of getting the work item path other than querying the work item info?
    // The work item tree provider does have it already, but couldn't access it through existing interface.
    // Would also prefer the keep the static path definition only at the server side.
    const currTreeDir: FSEntry | undefined = await getCurrRobotTreeContentDir();
    const workItemsResult: ActionResultWorkItems = await commands.executeCommand(ROBOCORP_LIST_WORK_ITEMS_INTERNAL, { robot: resolve(currTreeDir.filePath) });
    if (!workItemsResult.success) {
        return;
    }
    return workItemsResult.result;
}

async function queryNewWorkItemName(): Promise<string> {
    const filename: string = await vscode.window.showInputBox({
        'prompt': 'Please provide work item name',
        'ignoreFocusOut': true,
    });
    return filename;
}

async function createNewWorkItem(workItemInfo: WorkItemsInfo, workItemName: string): Promise<void> {
    if (!workItemInfo?.input_folder_path || !workItemName) {
        return;
    }

    const targetFolder = join(workItemInfo.input_folder_path, workItemName);
    const targetFile = join(targetFolder, 'work-items.json');
    try {
        await vscode.workspace.fs.createDirectory(Uri.file(targetFolder));
        await vscode.workspace.fs.writeFile(Uri.file(targetFile), Buffer.from(WORK_ITEM_TEMPLATE));
        vscode.window.showTextDocument(Uri.file(targetFile));
    } catch (err) {
        logError('Unable to create file.', err);
        vscode.window.showErrorMessage('Unable to create file. Error: ' + err.message);
    }
}

export async function newWorkItemInWorkItemsTree(): Promise<void> {
    const workItemInfo = await getWorkItemInfo();
    const workItemName = await queryNewWorkItemName();
    await createNewWorkItem(workItemInfo, workItemName);
}

export class WorkItemsTreeDataProvider extends RobotContentTreeDataProvider {
    private workItemsInfo: WorkItemsInfo = undefined;

    private async handleRoot(): Promise<FSEntry[]> {
        const elements: FSEntry[] = [];

        const robotsTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
        if (!robotsTree || robotsTree.selection.length == 0) {
            this.lastRobotEntry = undefined;
            return [{
                name: "<Waiting for Robot Selection...>",
                isDirectory: false,
                filePath: undefined,
            }];
        }

        const robotEntry: RobotEntry = robotsTree.selection[0];
        this.lastRobotEntry = robotEntry;

        const workItemsResult: ActionResultWorkItems = await commands.executeCommand(ROBOCORP_LIST_WORK_ITEMS_INTERNAL, { robot: resolve(this.lastRobotEntry.uri.fsPath) });
        if (!workItemsResult.success) {
            return elements;
        }

        this.workItemsInfo = workItemsResult.result;

        if (workItemsResult.result?.input_folder_path) {
            elements.push({
                name: basename(workItemsResult.result.input_folder_path),
                isDirectory: true,
                filePath: workItemsResult.result.input_folder_path,
            })
        }

        if (workItemsResult.result?.output_folder_path) {
            elements.push({
                name: basename(workItemsResult.result.output_folder_path),
                isDirectory: true,
                filePath: workItemsResult.result.output_folder_path,
            })
        }

        return elements;
    }

    private handleChild(element: FSEntry): FSEntry[] {
        let elements: FSEntry[] = [];

        // Work item query data is missing, return an empty tree, consider showing and error here?
        if (!this.workItemsInfo) {
            return elements;
        }

        if (element.name === 'work-items-in') {
            elements = this.workItemsInfo.input_work_items.map((work_item) => {
                return {
                    name: work_item.name,
                    isDirectory: false,
                    filePath: work_item.json_path,
                }
            })
        }

        if (element.name === 'work-items-out') {
            elements = this.workItemsInfo.output_work_items.map((work_item) => {
                return {
                    name: work_item.name,
                    isDirectory: false,
                    filePath: work_item.json_path,
                }
            })
        }

        return elements;
    }

    /**
     * If element is not defined, it's the root element.
     * Get the work item info from lsp when root is received and define the input and output folders.
     * Save the query to the object, so that every child object doesn't have to query the same data.
     *
     * With child elements list the found work items to the correct parent folder.
     *
     * @param element
     */
    async getChildren(element?: FSEntry): Promise<FSEntry[]> {
        let elements: FSEntry[] = [];

        if (!element) {
            elements = await this.handleRoot();
        } else {
            elements = this.handleChild(element)
        }

        return elements;
    }
}
