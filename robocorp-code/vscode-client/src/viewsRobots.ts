import * as vscode from "vscode";
import { OUTPUT_CHANNEL } from "./channel";
import { uriExists } from "./files";
import * as roboCommands from "./robocorpCommands";
import { basename, getSelectedRobot, RobotEntry, RobotEntryType } from "./viewsCommon";

let _globalSentMetric: boolean = false;

function empty<T>(array: T[]) {
    return array === undefined || array.length === 0;
}

function getRobotLabel(robotInfo: LocalRobotMetadataInfo): string {
    let label: string = undefined;
    if (robotInfo.yamlContents) {
        label = robotInfo.yamlContents["name"];
    }
    if (!label) {
        if (robotInfo.directory) {
            label = basename(robotInfo.directory);
        }
    }
    if (!label) {
        label = "";
    }
    return label;
}

export class RobotsTreeDataProvider implements vscode.TreeDataProvider<RobotEntry> {
    private _onDidChangeTreeData: vscode.EventEmitter<RobotEntry | null> = new vscode.EventEmitter<RobotEntry | null>();
    readonly onDidChangeTreeData: vscode.Event<RobotEntry | null> = this._onDidChangeTreeData.event;

    private _onForceSelectionFromTreeData: vscode.EventEmitter<RobotEntry[]> = new vscode.EventEmitter<RobotEntry[]>();
    readonly onForceSelectionFromTreeData: vscode.Event<RobotEntry[]> = this._onForceSelectionFromTreeData.event;

    private lastRoot: RobotEntry[] | undefined = undefined;

    fireRootChange() {
        this._onDidChangeTreeData.fire(null);
    }

    /**
     * Note that we make sure to only return valid entries here (i.e.: no entries
     * where RobotEntry.type === RobotEntryType.Error).
     */
    async getValidCachedOrComputeChildren(element?: RobotEntry): Promise<RobotEntry[]> {
        if (element === undefined) {
            if (this.lastRoot !== undefined) {
                let ret: RobotEntry[] = this.lastRoot.filter((e) => {
                    return e.type !== RobotEntryType.Error;
                });
                if (ret.length > 0) {
                    // We need to check whether entries still exist.
                    let foundAll: boolean = true;
                    for (const entry of ret) {
                        if (!(await uriExists(entry.uri))) {
                            foundAll = false;
                            break;
                        }
                    }
                    if (foundAll) {
                        return ret;
                    }
                }
            }
        }
        let ret: RobotEntry[] = await this.getChildren(element);
        // Remove any "error" entries
        return ret.filter((e) => {
            return e.type !== RobotEntryType.Error;
        });
    }

    /**
     * This function will compute the children and store the `lastRoot`
     * cache (if element === undefined).
     */
    async getChildren(element?: RobotEntry): Promise<RobotEntry[]> {
        let ret = await this.computeChildren(element);
        if (element === undefined) {
            // i.e.: this is the root entry, so, we've
            // collected the actual robots here.

            let notifySelection = false;
            if (empty(this.lastRoot) && empty(ret)) {
                // Don't notify of anything, nothing changed...
            } else if (empty(this.lastRoot)) {
                // We had nothing and now we have something, notify.
                if (!empty(ret)) {
                    notifySelection = true;
                }
            } else {
                // lastRoot is valid
                // We had something and now we have nothing, notify.
                if (empty(ret)) {
                    notifySelection = true;
                }
            }
            if (!empty(ret) && !notifySelection) {
                // Verify if the last selection is still valid (if it's not we need
                // to notify).
                let currentSelectedRobot = getSelectedRobot();
                let found = false;
                for (const entry of ret) {
                    if (currentSelectedRobot == entry) {
                        found = true;
                    }
                }
                if (!found) {
                    notifySelection = true;
                }
            }
            this.lastRoot = ret;

            if (notifySelection) {
                setTimeout(() => {
                    this._onForceSelectionFromTreeData.fire(this.lastRoot);
                }, 50);
            }

            if (ret.length === 0) {
                // No robot was actually found, so, we'll return a dummy entry
                // giving more instructions to the user.
                let added: boolean = false;
                for (const label of [
                    "No robots found.",
                    "Three ways to get started:",
                    "➔ Run the “Robocorp: Create Robot” action",
                    "➔ Open a robot folder (with a “robot.yaml” file)",
                    "➔ Open a parent folder (with multiple robots)",
                ]) {
                    ret.push({
                        "label": label,
                        "uri": undefined,
                        "robot": undefined,
                        "taskName": undefined,
                        "iconPath": added ? "" : "error",
                        "type": RobotEntryType.Error,
                        "parent": element,
                    });
                    added = true;
                }
            }
        }
        return ret;
    }

    async getParent?(element: RobotEntry): Promise<RobotEntry> {
        return element.parent;
    }

    async computeChildren(element?: RobotEntry): Promise<RobotEntry[]> {
        if (element) {
            if (element.type === RobotEntryType.Error) {
                return [];
            }

            // Get child elements.
            if (element.type === RobotEntryType.Task) {
                return []; // Tasks don't have children.
            }
            let yamlContents = element.robot.yamlContents;
            if (!yamlContents) {
                return [];
            }

            let tasks: object[] = yamlContents["tasks"];
            if (!tasks) {
                return [];
            }
            const robotInfo = element.robot;
            return Object.keys(tasks).map((task: string) => ({
                "label": task,
                "uri": vscode.Uri.file(robotInfo.filePath),
                "robot": robotInfo,
                "taskName": task,
                "iconPath": "debug-alt-small",
                "type": RobotEntryType.Task,
                "parent": element,
            }));
        }

        if (!_globalSentMetric) {
            _globalSentMetric = true;
            vscode.commands.executeCommand(roboCommands.ROBOCORP_SEND_METRIC, {
                "name": "vscode.treeview.used",
                "value": "1",
            });
        }

        // Get root elements.
        let actionResult: ActionResult<LocalRobotMetadataInfo[]> = await vscode.commands.executeCommand(
            roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
        );
        if (!actionResult.success) {
            OUTPUT_CHANNEL.appendLine(actionResult.message);
            return [];
        }
        let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

        if (empty(robotsInfo)) {
            return [];
        }

        return robotsInfo.map((robotInfo: LocalRobotMetadataInfo) => ({
            "label": getRobotLabel(robotInfo),
            "uri": vscode.Uri.file(robotInfo.filePath),
            "robot": robotInfo,
            "iconPath": "package",
            "type": RobotEntryType.Robot,
            "parent": element,
        }));
    }

    getTreeItem(element: RobotEntry): vscode.TreeItem {
        const isTask: boolean = element.type === RobotEntryType.Task;
        const treeItem = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.Collapsed);
        if (element.type === RobotEntryType.Robot) {
            treeItem.contextValue = "robotItem";
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.Expanded;
        } else if (isTask) {
            treeItem.contextValue = "taskItem";
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else if (element.type === RobotEntryType.Error) {
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        }
        if (element.iconPath) {
            treeItem.iconPath = new vscode.ThemeIcon(element.iconPath);
        }
        return treeItem;
    }
}
