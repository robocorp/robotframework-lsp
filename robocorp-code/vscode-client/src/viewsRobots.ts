import * as vscode from "vscode";
import { OUTPUT_CHANNEL } from "./channel";
import { uriExists } from "./files";
import { LocalRobotMetadataInfo, ActionResult } from "./protocols";
import * as roboCommands from "./robocorpCommands";
import { basename, getSelectedRobot, RobotEntry, RobotEntryType } from "./viewsCommon";
import { isActionPackage } from "./common";

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
                    "No Task nor Action Package found.",
                    "A few ways to get started:",
                    "➔ Run the “Robocorp: Create Task Package”",
                    "➔ Run the “Robocorp: Create Action Package”",
                    "➔ Open a Task Package folder (with a “robot.yaml” file)",
                    "➔ Open an Action Package folder (with a “package.yaml” file)",
                    "➔ Open a parent folder (with multiple Task or Action packages)",
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
            // Get child elements.
            if (element.type === RobotEntryType.Task) {
                return [
                    {
                        "label": "Run Task",
                        "uri": element.uri,
                        "robot": element.robot,
                        "taskName": element.taskName,
                        "iconPath": "run",
                        "type": RobotEntryType.Run,
                        "parent": element,
                    },
                    {
                        "label": "Debug Task",
                        "uri": element.uri,
                        "robot": element.robot,
                        "taskName": element.taskName,
                        "iconPath": "debug",
                        "type": RobotEntryType.Debug,
                        "parent": element,
                    },
                ];
            } else if (element.type === RobotEntryType.ActionPackage) {
                // TODO: We need a way to get the actions for the action package.
                let children = [];
                children.push({
                    "label": "Start Action Server",
                    "uri": element.uri,
                    "robot": element.robot,
                    "iconPath": "tools",
                    "type": RobotEntryType.StartActionServer,
                    "parent": element,
                    "tooltip": "Start the Action Server for the actions in the action package",
                });
                return children;
            } else if (element.type === RobotEntryType.Robot) {
                let yamlContents = element.robot.yamlContents;
                let robotChildren = [];
                if (yamlContents) {
                    let tasks: object[] = yamlContents["tasks"];
                    if (tasks) {
                        const robotInfo = element.robot;
                        robotChildren = Object.keys(tasks).map((task: string) => ({
                            "label": task,
                            "uri": vscode.Uri.file(robotInfo.filePath),
                            "robot": robotInfo,
                            "taskName": task,
                            "iconPath": "debug-alt-small",
                            "type": RobotEntryType.Task,
                            "parent": element,
                        }));
                    }
                }
                robotChildren.push({
                    "label": "Activities",
                    "uri": element.uri,
                    "robot": element.robot,
                    "iconPath": "tools",
                    "type": RobotEntryType.ActionsInRobot,
                    "parent": element,
                });
                return robotChildren;
            } else if (element.type === RobotEntryType.ActionsInRobot) {
                return [
                    {
                        "label": "Upload Task Package to Control Room",
                        "uri": element.uri,
                        "robot": element.robot,
                        "iconPath": "cloud-upload",
                        "type": RobotEntryType.UploadRobot,
                        "parent": element,
                    },
                    {
                        "label": "Open Task Package Terminal",
                        "uri": element.uri,
                        "robot": element.robot,
                        "iconPath": "terminal",
                        "type": RobotEntryType.RobotTerminal,
                        "parent": element,
                    },
                    {
                        "label": "Configure Tasks (robot.yaml)",
                        "uri": element.uri,
                        "robot": element.robot,
                        "iconPath": "go-to-file",
                        "type": RobotEntryType.OpenRobotYaml,
                        "parent": element,
                    },
                    {
                        "label": "Configure Dependencies (conda.yaml)",
                        "uri": element.uri,
                        "robot": element.robot,
                        "iconPath": "list-tree",
                        "type": RobotEntryType.OpenRobotCondaYaml,
                        "parent": element,
                    },
                    {
                        "label": "Open Flow Explorer",
                        "uri": element.uri,
                        "robot": element.robot,
                        "iconPath": "type-hierarchy-sub",
                        "type": RobotEntryType.OpenFlowExplorer,
                        "parent": element,
                    },
                ];
            } else if (element.type === RobotEntryType.Error) {
                return [];
            }

            OUTPUT_CHANNEL.appendLine("Unhandled in viewsRobots.ts: " + element.type);
            return [];
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

        const collapsed = robotsInfo.length > 1;
        return robotsInfo.map((robotInfo: LocalRobotMetadataInfo) => ({
            "label": getRobotLabel(robotInfo),
            "uri": vscode.Uri.file(robotInfo.filePath),
            "robot": robotInfo,
            "iconPath": "package",
            "type": isActionPackage(robotInfo) ? RobotEntryType.ActionPackage : RobotEntryType.Robot,
            "parent": element,
            "collapsed": collapsed,
        }));
    }

    getTreeItem(element: RobotEntry): vscode.TreeItem {
        const isTask: boolean = element.type === RobotEntryType.Task;
        const treeItem = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.Collapsed);
        if (element.type === RobotEntryType.Run) {
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
            treeItem.contextValue = "taskItemRun";
            treeItem.command = {
                "title": "Run",
                "command": roboCommands.ROBOCORP_ROBOTS_VIEW_TASK_RUN,
                "arguments": [element],
            };
        } else if (element.type === RobotEntryType.Debug) {
            treeItem.command = {
                "title": "Debug",
                "command": roboCommands.ROBOCORP_ROBOTS_VIEW_TASK_DEBUG,
                "arguments": [element],
            };
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
            treeItem.contextValue = "taskItemDebug";
        } else if (element.type === RobotEntryType.ActionsInRobot) {
            treeItem.contextValue = "actionsInRobotItem";
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.Expanded;
        } else if (element.type === RobotEntryType.OpenRobotYaml) {
            treeItem.command = {
                "title": "Configure Robot (robot.yaml)",
                "command": roboCommands.ROBOCORP_OPEN_ROBOT_TREE_SELECTION,
                "arguments": [element],
            };
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else if (element.type === RobotEntryType.OpenRobotCondaYaml) {
            treeItem.command = {
                "title": "Configure Dependencies (conda.yaml)",
                "command": roboCommands.ROBOCORP_OPEN_ROBOT_CONDA_TREE_SELECTION,
                "arguments": [element],
            };
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else if (element.type === RobotEntryType.RobotTerminal) {
            treeItem.command = {
                "title": "Open Robot Terminal",
                "command": roboCommands.ROBOCORP_CREATE_RCC_TERMINAL_TREE_SELECTION,
                "arguments": [element],
            };
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else if (element.type === RobotEntryType.OpenFlowExplorer) {
            treeItem.command = {
                "title": "Open Flow Explorer",
                "command": "robot.openFlowExplorer",
                "arguments": [vscode.Uri.file(element.robot.directory).toString()],
            };
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else if (element.type === RobotEntryType.UploadRobot) {
            treeItem.command = {
                "title": "Upload Robot to Control Room",
                "command": roboCommands.ROBOCORP_CLOUD_UPLOAD_ROBOT_TREE_SELECTION,
                "arguments": [element],
            };
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else if (element.type === RobotEntryType.Robot) {
            treeItem.contextValue = "robotItem";
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.Expanded;
        } else if (isTask) {
            treeItem.contextValue = "taskItem";
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.Expanded;
        } else if (element.type === RobotEntryType.Error) {
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else if (element.type === RobotEntryType.StartActionServer) {
            treeItem.command = {
                "title": "Start Action Server",
                "command": roboCommands.ROBOCORP_START_ACTION_SERVER,
                "arguments": [vscode.Uri.file(element.robot.directory)],
            };
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
        }
        if (element.tooltip) {
            treeItem.tooltip = element.tooltip;
        }
        if (element.iconPath) {
            treeItem.iconPath = new vscode.ThemeIcon(element.iconPath);
        }
        if (element.collapsed !== undefined) {
            treeItem.collapsibleState = element.collapsed
                ? vscode.TreeItemCollapsibleState.Collapsed
                : vscode.TreeItemCollapsibleState.Expanded;
        }
        return treeItem;
    }
}
