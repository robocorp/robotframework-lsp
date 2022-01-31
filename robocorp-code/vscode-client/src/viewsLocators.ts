import * as vscode from "vscode";
import * as roboCommands from "./robocorpCommands";
import { getSelectedRobot, LocatorEntry, RobotEntry } from "./viewsCommon";

export class LocatorsTreeDataProvider implements vscode.TreeDataProvider<LocatorEntry> {
    private _onDidChangeTreeData: vscode.EventEmitter<LocatorEntry | null> =
        new vscode.EventEmitter<LocatorEntry | null>();
    readonly onDidChangeTreeData: vscode.Event<LocatorEntry | null> = this._onDidChangeTreeData.event;

    private lastRobotEntry: RobotEntry = undefined;

    fireRootChange() {
        this._onDidChangeTreeData.fire(null);
    }

    async onRobotsTreeSelectionChanged(robotEntry: RobotEntry | undefined) {
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

    async getChildren(element?: LocatorEntry): Promise<LocatorEntry[]> {
        // i.e.: the contents of this tree depend on what's selected in the robots tree.
        const robotEntry: RobotEntry = getSelectedRobot();
        if (!robotEntry) {
            this.lastRobotEntry = undefined;
            return [
                {
                    name: "<Waiting for Robot Selection...>",
                    type: "info",
                    line: 0,
                    column: 0,
                    filePath: undefined,
                },
            ];
        }
        let actionResult: ActionResult<LocatorEntry[]> = await vscode.commands.executeCommand(
            roboCommands.ROBOCORP_GET_LOCATORS_JSON_INFO,
            { "robotYaml": robotEntry.robot.filePath }
        );
        if (!actionResult["success"]) {
            this.lastRobotEntry = undefined;
            return [
                {
                    name: actionResult.message,
                    type: "error",
                    line: 0,
                    column: 0,
                    filePath: robotEntry.robot.filePath,
                },
            ];
        }

        this.lastRobotEntry = robotEntry;
        return actionResult["result"];
    }

    getTreeItem(element: LocatorEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(element.name);

        // https://microsoft.github.io/vscode-codicons/dist/codicon.html
        let iconPath = "file-media";
        if (element.type === "browser") {
            iconPath = "browser";
        } else if (element.type === "error") {
            iconPath = "error";
        }
        // Only add context to actual locator items
        if (element.type !== "error") {
            treeItem.contextValue = "locatorEntry";
        }
        treeItem.iconPath = new vscode.ThemeIcon(iconPath);
        return treeItem;
    }
}
