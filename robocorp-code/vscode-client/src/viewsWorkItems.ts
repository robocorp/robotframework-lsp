import * as vscode from "vscode";
import { resolve, join, dirname, basename } from "path";

import { logError } from "./channel";
import { ROBOCORP_LIST_WORK_ITEMS_INTERNAL, ROBOCORP_VERIFY_LIBRARY_VERSION_INTERNAL } from "./robocorpCommands";
import { FSEntry, RobotEntry, treeViewIdToTreeDataProvider, treeViewIdToTreeView } from "./viewsCommon";
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE, TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE } from "./robocorpViews";
import { getCurrRobotDir, RobotSelectionTreeDataProviderBase } from "./viewsRobotSelection";
import { resolveInterpreter } from "./activities";
import { feedback } from "./rcc";

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

export interface WorkItemFSEntry extends FSEntry {
    name: string;
    isDirectory: boolean;
    filePath: string;
    kind: "outputWorkItem" | "inputWorkItem" | "outputWorkItemDir" | "inputWorkItemDir" | undefined;
    workItem?: WorkItem; // Only available for outputWorkItem and inputWorkItem
}

async function getWorkItemInfo(): Promise<WorkItemsInfo | null> {
    let workItemsTreeDataProvider: WorkItemsTreeDataProvider = <WorkItemsTreeDataProvider>(
        treeViewIdToTreeDataProvider.get(TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE)
    );

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
        ROBOCORP_LIST_WORK_ITEMS_INTERNAL,
        { robot: resolve(currTreeDir.filePath), "increment_output": false }
    );
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
    const targetFile = join(targetFolder, "work-items.json");
    try {
        let fileUri = vscode.Uri.file(targetFile);
        try {
            await vscode.workspace.fs.stat(fileUri); // this will raise if the file doesn't exist.

            let OVERRIDE = "Override";
            let ret = await vscode.window.showInformationMessage(
                "File " + targetFile + " already exists.",
                { "modal": true },
                OVERRIDE
            );
            if (ret != OVERRIDE) {
                return;
            }
        } catch (err) {
            // ok, file does not exist
        }
        // No need to await.
        feedback("vscode.workitem.input.created");

        await vscode.workspace.fs.createDirectory(vscode.Uri.file(targetFolder));
        await vscode.workspace.fs.writeFile(fileUri, Buffer.from(WORK_ITEM_TEMPLATE));
        vscode.window.showTextDocument(fileUri);
    } catch (err) {
        logError("Unable to create file.", err, "WORK_ITEM_CREATE");
        vscode.window.showErrorMessage("Unable to create file. Error: " + err.message);
    }
}

export async function convertOutputWorkItemToInput(item: WorkItemFSEntry): Promise<void> {
    if (item && item.kind == "outputWorkItem" && item.workItem) {
        let workItemInfo = await getWorkItemInfo();
        if (!workItemInfo?.input_folder_path) {
            vscode.window.showErrorMessage(
                "Unable to convert output work item to input because input folder could not be found."
            );
            return;
        }

        let workItemName: string = await vscode.window.showInputBox({
            "prompt": "Please provide name for converted input work item",
            "ignoreFocusOut": true,
        });

        if (!workItemName) {
            return;
        }
        let target = join(workItemInfo.input_folder_path, workItemName);
        try {
            let stat = await vscode.workspace.fs.stat(vscode.Uri.file(target));
            // Target already exists...
            let OVERRIDE = "Override";
            let ret = await vscode.window.showInformationMessage(
                "File " + target + " already exists.",
                { "modal": true },
                OVERRIDE
            );
            if (ret != OVERRIDE) {
                return;
            }
        } catch (error) {
            // Ok, does not exist
        }

        try {
            let workItem: WorkItem = item.workItem;

            // Call to make sure that it exists.
            await vscode.workspace.fs.createDirectory(vscode.Uri.file(workItemInfo.input_folder_path));

            await vscode.workspace.fs.copy(
                vscode.Uri.file(dirname(workItem.json_path)), // src
                vscode.Uri.file(target), // dest
                { "overwrite": true }
            );
            vscode.window.showInformationMessage("Finished converting output work item to input work item.");
        } catch (error) {
            let msg = "Error converting output work item to input.";
            logError(msg, error, "WORKITEM_CONVERT");
            vscode.window.showErrorMessage(msg);
        }
    }
}

export async function newWorkItemInWorkItemsTree(): Promise<void> {
    const workItemInfo = await getWorkItemInfo();

    let workItemName: string = await vscode.window.showInputBox({
        "prompt": "Please provide work item name",
        "ignoreFocusOut": true,
    });
    await createNewWorkItem(workItemInfo, workItemName);
}

export async function deleteWorkItemInWorkItemsTree(item: WorkItemFSEntry): Promise<void> {
    if (!item || !item.filePath) {
        await vscode.window.showInformationMessage("No robot selected for work item deletion.");
        return undefined;
    }

    const workItemPath = dirname(item.filePath);
    let uri = vscode.Uri.file(workItemPath);
    let stat: vscode.FileStat;
    try {
        stat = await vscode.workspace.fs.stat(uri);
    } catch (err) {
        // unable to get stat (file may have been removed in the meanwhile).
    }
    if (stat) {
        try {
            await vscode.workspace.fs.delete(uri, { recursive: true, useTrash: true });
        } catch (err) {
            let DELETE_PERMANENTLY = "Delete permanently";
            let msg = await vscode.window.showErrorMessage(
                "Unable to move to trash: " + workItemPath + ". How to proceed?",
                { "modal": true },
                DELETE_PERMANENTLY
            );
            if (msg == DELETE_PERMANENTLY) {
                await vscode.workspace.fs.delete(uri, { recursive: true, useTrash: false });
            } else {
                return;
            }
        }
    }
}

export function openWorkItemHelp() {
    vscode.env.openExternal(
        vscode.Uri.parse(
            "https://robocorp.com/docs/developer-tools/visual-studio-code/extension-features#using-work-items"
        )
    );
}

export class WorkItemsTreeDataProvider extends RobotSelectionTreeDataProviderBase {
    private workItemsInfo: WorkItemsInfo | undefined = undefined;

    protected PATTERN_TO_LISTEN: string = "**/devdata/**";

    public getWorkItemsInfo(): WorkItemsInfo | undefined {
        return this.workItemsInfo;
    }

    private async handleRoot(): Promise<WorkItemFSEntry[]> {
        const elements: WorkItemFSEntry[] = [];

        const robotsTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
        if (!robotsTree || robotsTree.selection.length == 0) {
            this.lastRobotEntry = undefined;
            return [
                {
                    name: "<Waiting for Robot Selection...>",
                    isDirectory: false,
                    filePath: undefined,
                    kind: undefined,
                },
            ];
        }

        const robotEntry: RobotEntry = robotsTree.selection[0];
        this.lastRobotEntry = robotEntry;

        let robot = resolve(this.lastRobotEntry.uri.fsPath);

        const workItemsResult: ActionResultWorkItems = await vscode.commands.executeCommand(
            ROBOCORP_LIST_WORK_ITEMS_INTERNAL,
            { "robot": robot, "increment_output": false }
        );

        if (!workItemsResult.success) {
            this.workItemsInfo = undefined;
            return [
                {
                    name: workItemsResult.message,
                    isDirectory: false,
                    filePath: undefined,
                    kind: undefined,
                },
            ];
        }

        this.workItemsInfo = workItemsResult.result;

        let hasInputFolder = workItemsResult.result?.input_folder_path;
        let hasOutputFolder = workItemsResult.result?.output_folder_path;

        if (hasInputFolder || hasOutputFolder) {
            let errorMsg = await this.collectRpaFrameworkRequirementsErrorMessage(robot);
            if (errorMsg) {
                elements.push({
                    name: errorMsg,
                    isDirectory: false,
                    filePath: undefined,
                    kind: undefined,
                });
            }
        }

        if (hasInputFolder) {
            elements.push({
                name: basename(workItemsResult.result.input_folder_path),
                isDirectory: true,
                filePath: workItemsResult.result.input_folder_path,
                kind: "inputWorkItemDir",
            });
        }

        if (hasOutputFolder) {
            elements.push({
                name: basename(workItemsResult.result.output_folder_path),
                isDirectory: true,
                filePath: workItemsResult.result.output_folder_path,
                kind: "outputWorkItemDir",
            });
        }

        return elements;
    }

    /**
     *
     * @returns an error message if something isn't correct with the rpa framework or an empty string otherwise.
     */
    private async collectRpaFrameworkRequirementsErrorMessage(robot: string): Promise<string> {
        let interpreter: InterpreterInfo | undefined = undefined;
        let interpreterResult = await resolveInterpreter(robot);
        let msg: string = "";

        if (!interpreterResult.success) {
            return "Error resolving interpreter info: " + interpreterResult.message;
        }
        interpreter = interpreterResult.result;
        if (!interpreter) {
            return "Unable to resolve interpreter for: " + robot;
        }
        if (!interpreter.environ) {
            return "Unable to resolve interpreter environment based on: " + robot;
        }

        let env = interpreter.environ;
        let condaPrefix = env["CONDA_PREFIX"];
        if (!condaPrefix) {
            return "CONDA_PREFIX not available in environment.";
        }

        let libraryVersionInfoActionResult: LibraryVersionInfoDict;
        try {
            libraryVersionInfoActionResult = await vscode.commands.executeCommand(
                ROBOCORP_VERIFY_LIBRARY_VERSION_INTERNAL,
                {
                    "conda_prefix": condaPrefix,
                    "library": "rpaframework",
                    "version": "11.3",
                }
            );

            if (!libraryVersionInfoActionResult["success"]) {
                return libraryVersionInfoActionResult["message"];
            }
        } catch (error) {
            msg = "Error verifying rpaframework version.";
            logError(msg, error, "WORKITEM_VERIFY_RPA_VERSION");
            return msg;
        }
        return "";
    }

    private handleChild(element: WorkItemFSEntry): WorkItemFSEntry[] {
        let elements: WorkItemFSEntry[] = [];

        if (!this.workItemsInfo) {
            return elements;
        }

        if (element.name === "work-items-in") {
            elements = this.workItemsInfo.input_work_items.map((workItem) => {
                return {
                    name: workItem.name,
                    isDirectory: false,
                    filePath: workItem.json_path,
                    kind: "inputWorkItem",
                    workItem: workItem,
                };
            });
        }

        if (element.name === "work-items-out") {
            elements = this.workItemsInfo.output_work_items.map((workItem) => {
                return {
                    name: workItem.name,
                    isDirectory: false,
                    filePath: workItem.json_path,
                    kind: "outputWorkItem",
                    workItem: workItem,
                };
            });
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
    async getChildren(element?: WorkItemFSEntry): Promise<WorkItemFSEntry[]> {
        let elements: WorkItemFSEntry[] = [];

        if (!element) {
            elements = await this.handleRoot();
        } else {
            elements = this.handleChild(element);
        }

        return elements;
    }

    getTreeItem(element: WorkItemFSEntry): vscode.TreeItem {
        let treeItem = super.getTreeItem(element);

        if (element.isDirectory) {
            // Make directory expanded by default.
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.Expanded;
        }
        if (element.kind) {
            treeItem.contextValue = element.kind;
        }
        return treeItem;
    }
}
