import * as vscode from "vscode";
import * as roboCommands from "./robocorpCommands";
import { CloudEntry, treeViewIdToTreeDataProvider } from "./viewsCommon";
import { ROBOCORP_SUBMIT_ISSUE } from "./robocorpCommands";
import { TREE_VIEW_ROBOCORP_CLOUD_TREE } from "./robocorpViews";
import { getWorkspaceDescription } from "./ask";
import { logError } from "./channel";

export class CloudTreeDataProvider implements vscode.TreeDataProvider<CloudEntry> {
    private _onDidChangeTreeData: vscode.EventEmitter<CloudEntry | null> = new vscode.EventEmitter<CloudEntry | null>();
    readonly onDidChangeTreeData: vscode.Event<CloudEntry | null> = this._onDidChangeTreeData.event;

    public refreshOnce = false;

    fireRootChange() {
        this._onDidChangeTreeData.fire(null);
    }

    private async _fillRoots(ret: CloudEntry[]) {
        let accountInfoResult: ActionResult<any> = await vscode.commands.executeCommand(
            roboCommands.ROBOCORP_GET_LINKED_ACCOUNT_INFO_INTERNAL
        );

        if (!accountInfoResult.success) {
            ret.push({
                "label": "Link to Control Room",
                "iconPath": "link",
                "viewItemContextValue": "cloudLoginItem",
                "command": {
                    "title": "Link to Control Room",
                    "command": roboCommands.ROBOCORP_CLOUD_LOGIN,
                },
            });
        } else {
            let accountInfo = accountInfoResult.result;
            ret.push({
                "label": "Linked: " + accountInfo["fullname"] + " (" + accountInfo["email"] + ")",
                "iconPath": "link",
                "viewItemContextValue": "cloudLogoutItem",
            });

            let vaultInfoResult: ActionResult<any> = await vscode.commands.executeCommand(
                roboCommands.ROBOCORP_GET_CONNECTED_VAULT_WORKSPACE_INTERNAL
            );

            if (!vaultInfoResult || !vaultInfoResult.success || !vaultInfoResult.result) {
                ret.push({
                    "label": "Vault: disconnected.",
                    "iconPath": "unlock",
                    "viewItemContextValue": "vaultDisconnected",
                });
            } else {
                const result: IVaultInfo = vaultInfoResult.result;
                ret.push({
                    "label": "Vault: connected to: " + getWorkspaceDescription(result),
                    "iconPath": "lock",
                    "viewItemContextValue": "vaultConnected",
                });
            }
        }
    }

    async getChildren(element?: CloudEntry): Promise<CloudEntry[]> {
        if (!element) {
            let ret: CloudEntry[] = [];
            try {
                await this._fillRoots(ret);
                ret.push({
                    "label": "Robot Development Guide",
                    "iconPath": "book",
                    "command": {
                        "title": "Open https://robocorp.com/docs/development-guide",
                        "command": "vscode.open",
                        "arguments": [vscode.Uri.parse("https://robocorp.com/docs/development-guide")],
                    },
                });
                ret.push({
                    "label": "Keyword Libraries Documentation",
                    "iconPath": "notebook",
                    "command": {
                        "title": "Open https://robocorp.com/docs/libraries",
                        "command": "vscode.open",
                        "arguments": [vscode.Uri.parse("https://robocorp.com/docs/libraries")],
                    },
                });
            } catch (error) {
                logError("Error getting children", error, "VIEWS_CLOUD_COMPUTE_ROOTS");
                ret.push({
                    "label": "Error initializing. Click to see Output > Robocorp Code.",
                    "iconPath": "error",
                    "command": {
                        "title": "See output",
                        "command": roboCommands.ROBOCORP_SHOW_OUTPUT,
                    },
                });
            }
            ret.push({
                "label": "Submit issue to Robocorp",
                "iconPath": "report",
                "command": {
                    "title": "Submit issue to Robocorp",
                    "command": ROBOCORP_SUBMIT_ISSUE,
                },
            });

            return ret;
        }
        if (element.children) {
            return element.children;
        }
        return [];
    }

    getTreeItem(element: CloudEntry): vscode.TreeItem {
        const treeItem = new vscode.TreeItem(
            element.label,
            element.children ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None
        );
        treeItem.command = element.command;
        treeItem.iconPath = new vscode.ThemeIcon(element.iconPath);
        if (element.viewItemContextValue) {
            treeItem.contextValue = element.viewItemContextValue;
        }
        return treeItem;
    }
}

export function refreshCloudTreeView() {
    let dataProvider: CloudTreeDataProvider = <CloudTreeDataProvider>(
        treeViewIdToTreeDataProvider.get(TREE_VIEW_ROBOCORP_CLOUD_TREE)
    );
    if (dataProvider) {
        dataProvider.refreshOnce = true;
        dataProvider.fireRootChange();
    }
}
