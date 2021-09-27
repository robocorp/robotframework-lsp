import * as vscode from 'vscode';
import { basename, dirname } from 'path';

import { debounce, FSEntry, getSelectedRobot, RobotEntry, treeViewIdToTreeView } from './viewsCommon';
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE } from './robocorpViews';

export async function getCurrRobotDir(): Promise<FSEntry | undefined> {
  let robotContentTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
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

export class RobotSelectionTreeDataProviderBase implements vscode.TreeDataProvider<FSEntry> {

  private _onDidChangeTreeData: vscode.EventEmitter<FSEntry | null> = new vscode.EventEmitter<FSEntry | null>();
  readonly onDidChangeTreeData: vscode.Event<FSEntry | null> = this._onDidChangeTreeData.event;

  protected lastRobotEntry: RobotEntry = undefined;
  private lastWatcher: vscode.FileSystemWatcher | undefined = undefined;

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
      let watcher: vscode.FileSystemWatcher = vscode.workspace.createFileSystemWatcher('**/' + d + '/**', false, true, false);
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

  async onTreeSelectionChanged(robotContentTree: vscode.TreeView<FSEntry>) {
      let selection = robotContentTree.selection;
      if (selection.length == 1) {
          let entry: FSEntry = selection[0];
          if (entry.filePath && !entry.isDirectory) {
              let uri = vscode.Uri.file(entry.filePath);
              let document = await vscode.workspace.openTextDocument(uri);
              if (document) {
                  await vscode.window.showTextDocument(document);
              }
          }
      }
  }

  async getChildren(element: FSEntry): Promise<FSEntry[]> {
    throw new Error('Not implemented');
  };

  getTreeItem(element: FSEntry): vscode.TreeItem {
      const treeItem = new vscode.TreeItem(element.name);
      if (element.isDirectory) {
          treeItem.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
      } else {
          treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
      }

      if (element.filePath === undefined) {
          // https://microsoft.github.io/vscode-codicons/dist/codicon.html
          treeItem.iconPath = new vscode.ThemeIcon("error");
      } else if (element.isDirectory) {
          treeItem.iconPath = vscode.ThemeIcon.Folder;
          treeItem.resourceUri = vscode.Uri.file(element.filePath);
      } else {
          treeItem.iconPath = vscode.ThemeIcon.File;
          treeItem.resourceUri = vscode.Uri.file(element.filePath);
      }
      return treeItem;
  }
}