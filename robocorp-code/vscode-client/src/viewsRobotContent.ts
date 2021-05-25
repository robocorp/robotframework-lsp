import * as vscode from 'vscode';
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE } from './robocorpViews';
import { FSEntry, getSelectedRobot, RobotEntry, treeViewIdToTreeView } from './viewsCommon';



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
        // i.e.: the contents of this tree depend on what's selected in the robots tree.
        const robotsTree = treeViewIdToTreeView.get(TREE_VIEW_ROBOCORP_ROBOTS_TREE);
        if (!robotsTree || robotsTree.selection.length == 0) {
            this.lastRobotEntry = undefined;
            return [{
                name: "<Waiting for Robot Selection...>",
                filePath: undefined,
            }];
        }
        let robotEntry: RobotEntry = robotsTree.selection[0];
        this.lastRobotEntry = robotEntry;
        let locatorInfo: FSEntry[] = [{
            name: "... get robot contents ...",
            filePath: undefined,
        }];
        return locatorInfo;
    }

    getTreeItem(element: FSEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(element.name);

        // https://microsoft.github.io/vscode-codicons/dist/codicon.html
        let iconPath = "file-media";
        if (element.filePath === undefined) {
            iconPath = "error";

        }
        treeItem.iconPath = new vscode.ThemeIcon(iconPath);
        return treeItem;
    }
}
