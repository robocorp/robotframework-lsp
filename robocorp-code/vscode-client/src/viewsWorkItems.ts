import * as vscode from 'vscode';
import { resolve, join, dirname, basename } from 'path';

import { logError } from './channel';
import { ROBOCORP_LIST_WORK_ITEMS_INTERNAL } from "./robocorpCommands";
import { FSEntry, RobotEntry, treeViewIdToTreeView } from "./viewsCommon";
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
  // Would there be a faster way of getting the work item path other than querying the work item info?
  // The work item tree provider does have it already, but couldn't access it through existing interface.
  // Would also prefer the keep the static path definition only at the server side.
  const currTreeDir: FSEntry | undefined = await getCurrRobotDir();
  const workItemsResult: ActionResultWorkItems = await vscode.commands.executeCommand(ROBOCORP_LIST_WORK_ITEMS_INTERNAL, { robot: resolve(currTreeDir.filePath) });
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
      await vscode.workspace.fs.createDirectory(vscode.Uri.file(targetFolder));
      await vscode.workspace.fs.writeFile(vscode.Uri.file(targetFile), Buffer.from(WORK_ITEM_TEMPLATE));
      vscode.window.showTextDocument(vscode.Uri.file(targetFile));
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

export async function deleteWorkItemInWorkItemsTree(): Promise<void> {
  let robotContentTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_WORK_ITEMS_TREE);
  if (!robotContentTree) {
      return undefined;
  }

  let selection: FSEntry[] = robotContentTree.selection;
  if (!selection) {
      await vscode.window.showInformationMessage("No work item selected for deletion.")
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

export class WorkItemsTreeDataProvider extends RobotSelectionTreeDataProviderBase {
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

      const workItemsResult: ActionResultWorkItems = await vscode.commands.executeCommand(ROBOCORP_LIST_WORK_ITEMS_INTERNAL, { robot: resolve(this.lastRobotEntry.uri.fsPath) });
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
