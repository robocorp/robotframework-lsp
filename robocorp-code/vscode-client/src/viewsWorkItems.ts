import * as vscode from 'vscode';
import { resolve, join, dirname, basename } from 'path';

import { logError } from './channel';
import { ROBOCORP_LIST_WORK_ITEMS_INTERNAL } from "./robocorpCommands";
import { FSEntry, RobotEntry, treeViewIdToTreeDataProvider, treeViewIdToTreeView } from "./viewsCommon";
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE, TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE } from './robocorpViews';
import { getCurrRobotDir, RobotSelectionTreeDataProviderBase } from './viewsRobotSelection';

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
    let workItemsTreeDataProvider: WorkItemsTreeDataProvider = <WorkItemsTreeDataProvider>treeViewIdToTreeDataProvider.get(
        TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE);

    if (workItemsTreeDataProvider) {
        let workItemsInfo = workItemsTreeDataProvider.getWorkItemsInfo();
        if (workItemsInfo) {
            // If the tree is available and the info was loaded, use it.
            return workItemsInfo;
        }
    }

    // In general we shouldn't really use this code (as the action which uses this function
    // can only be activated from the tree, but let's leave it as a fallback in case we
    // do want it in the future).
    const currTreeDir: FSEntry | undefined = await getCurrRobotDir();
    if (!currTreeDir) {
        return;
    }
    const workItemsResult: ActionResultWorkItems = await vscode.commands.executeCommand(
        ROBOCORP_LIST_WORK_ITEMS_INTERNAL, { robot: resolve(currTreeDir.filePath) });
    if (!workItemsResult.success) {
        return;
    }
    return workItemsResult.result;
}


async function createNewWorkItem(workItemInfo: WorkItemsInfo, workItemName: string): Promise<void> {
    if (workItemName) {
        workItemName = workItemName.trim();
    }
    if (!workItemInfo?.input_folder_path || !workItemName) {
        return;
    }

    const targetFolder = join(workItemInfo.input_folder_path, workItemName);
    const targetFile = join(targetFolder, 'work-items.json');
    try {
        let fileUri = vscode.Uri.file(targetFile);
        try {
            await vscode.workspace.fs.stat(fileUri); // this will raise if the file doesn't exist.

            let OVERRIDE = "Override";
            let ret = await vscode.window.showInformationMessage(
                "File " + targetFile + " already exists.", { "modal": true }, OVERRIDE);
            if (ret != OVERRIDE) {
                return;
            }
        } catch (err) {
            // ok, file does not exist
        }
        await vscode.workspace.fs.createDirectory(vscode.Uri.file(targetFolder));
        await vscode.workspace.fs.writeFile(fileUri, Buffer.from(WORK_ITEM_TEMPLATE));
        vscode.window.showTextDocument(fileUri);
    } catch (err) {
        logError('Unable to create file.', err);
        vscode.window.showErrorMessage('Unable to create file. Error: ' + err.message);
    }
}

export async function newWorkItemInWorkItemsTree(): Promise<void> {
    const workItemInfo = await getWorkItemInfo();

    let workItemName: string = await vscode.window.showInputBox({
        'prompt': 'Please provide work item name',
        'ignoreFocusOut': true,
    });
    await createNewWorkItem(workItemInfo, workItemName);
}

export async function deleteWorkItemInWorkItemsTree(): Promise<void> {
    let workItemsTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE);
    if (!workItemsTree) {
        await vscode.window.showInformationMessage("No robot selected for work item deletion.");
        return undefined;
    }

    let selection: FSEntry[] = workItemsTree.selection;
    if (!selection || selection.length === 0) {
        await vscode.window.showInformationMessage("No work item selected for deletion.");
        return;
    }

    for (const entry of selection) {
        let uri = vscode.Uri.file(entry.filePath);
        let stat: vscode.FileStat;
        try {
            stat = await vscode.workspace.fs.stat(uri);
        } catch (err) {
            // unable to get stat (file may have been removed in the meanwhile).
        }
        if (stat) {
            // Remove the whole work item directory and it's contents if file is selected
            if (stat.type === vscode.FileType.File) {
                uri = vscode.Uri.file(dirname(uri.fsPath));
            }
            try {
                await vscode.workspace.fs.delete(uri, { recursive: true, useTrash: true });
            } catch (err) {
                let DELETE_PERMANENTLY = "Delete permanently";
                let msg = await vscode.window.showErrorMessage(
                    "Unable to move to trash: " + entry.filePath + ". How to proceed?",
                    { "modal": true },
                    DELETE_PERMANENTLY)
                if (msg == DELETE_PERMANENTLY) {
                    await vscode.workspace.fs.delete(uri, { recursive: true, useTrash: false });
                } else {
                    return;
                }
            }
        }
    }
}

export function openWorkItemHelp() {
    vscode.env.openExternal(vscode.Uri.parse('https://robocorp.com/docs/development-guide/control-room/data-pipeline#what-is-a-work-item'));
}

export class WorkItemsTreeDataProvider extends RobotSelectionTreeDataProviderBase {
    private workItemsInfo: WorkItemsInfo | undefined = undefined;

    protected PATTERN_TO_LISTEN: string = "**/devdata/**";

    public getWorkItemsInfo(): WorkItemsInfo | undefined {
        return this.workItemsInfo;
    }

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

        const workItemsResult: ActionResultWorkItems = await vscode.commands.executeCommand(
            ROBOCORP_LIST_WORK_ITEMS_INTERNAL, { robot: resolve(this.lastRobotEntry.uri.fsPath) });

        if (!workItemsResult.success) {
            this.workItemsInfo = undefined;
            return [{
                name: workItemsResult.message,
                isDirectory: false,
                filePath: undefined,
            }];
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

    getTreeItem(element: FSEntry): vscode.TreeItem {
        let treeItem = super.getTreeItem(element);

        if (element.isDirectory) {
            // Make directory expanded by default.
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.Expanded;
        }
        return treeItem;
    }
}
