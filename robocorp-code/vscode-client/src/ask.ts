import * as roboCommands from "./robocorpCommands";
import { commands, QuickPickItem, window } from "vscode";
import { WorkspaceInfo, IVaultInfo, ListWorkspacesActionResult } from "./protocols";

export interface QuickPickItemWithAction extends QuickPickItem {
    action: any;
    sortKey?: string;
}

export interface QuickPickItemRobotTask extends QuickPickItem {
    robotYaml: string;
    taskName: string;
    keyInLRU: string;
}

export function sortCaptions(captions: QuickPickItemWithAction[]) {
    captions.sort(function (a, b) {
        if (a.sortKey < b.sortKey) {
            return -1;
        }
        if (a.sortKey > b.sortKey) {
            return 1;
        }

        if (a.label < b.label) {
            return -1;
        }
        if (a.label > b.label) {
            return 1;
        }

        return 0;
    });
}

export async function showSelectOneQuickPick(
    items: QuickPickItemWithAction[],
    message: string,
    title?: string
): Promise<QuickPickItemWithAction> {
    let selectedItem: QuickPickItemWithAction = await window.showQuickPick(items, {
        "canPickMany": false,
        "placeHolder": message,
        "ignoreFocusOut": true,
        "title": title,
    });
    return selectedItem;
}

export async function showSelectOneStrQuickPick(items: string[], message: string, title?: string): Promise<string> {
    let selectedItem: string = await window.showQuickPick(items, {
        "canPickMany": false,
        "placeHolder": message,
        "ignoreFocusOut": true,
        "title": title,
    });
    return selectedItem;
}

export function getWorkspaceDescription(wsInfo: WorkspaceInfo | IVaultInfo) {
    return wsInfo.organizationName + ": " + wsInfo.workspaceName;
}

interface IWorkspacesAndSelected {
    workspaceInfo: WorkspaceInfo[];
    selectedWorkspaceInfo: WorkspaceInfo;
}

export async function selectWorkspace(title: string, refresh: boolean): Promise<undefined | IWorkspacesAndSelected> {
    SELECT_OR_REFRESH: do {
        // We ask for the information on the existing workspaces information.
        // Note that this may be cached from the last time it was asked,
        // so, we have an option to refresh it (and ask again).
        let actionResult: ListWorkspacesActionResult = await commands.executeCommand(
            roboCommands.ROBOCORP_CLOUD_LIST_WORKSPACES_INTERNAL,
            { "refresh": refresh }
        );

        if (!actionResult.success) {
            window.showErrorMessage("Error listing Control Room workspaces: " + actionResult.message);
            return undefined;
        }

        let workspaceInfo: WorkspaceInfo[] = actionResult.result;
        if (!workspaceInfo || workspaceInfo.length == 0) {
            window.showErrorMessage("A Control Room Workspace must be created to submit a Robot to the Control Room.");
            return undefined;
        }

        // Now, if there are only a few items or a single workspace,
        // just show it all, otherwise do a pre-selectedItem with the workspace.
        let workspaceIdFilter: string = undefined;

        if (workspaceInfo.length > 1) {
            // Ok, there are many workspaces, let's provide a pre-filter for it.
            let captions: QuickPickItemWithAction[] = new Array();
            for (let i = 0; i < workspaceInfo.length; i++) {
                const wsInfo: WorkspaceInfo = workspaceInfo[i];
                let caption: QuickPickItemWithAction = {
                    "label": "$(folder) " + getWorkspaceDescription(wsInfo),
                    "action": { "filterWorkspaceId": wsInfo.workspaceId, "wsInfo": wsInfo },
                };
                captions.push(caption);
            }

            sortCaptions(captions);

            let caption: QuickPickItemWithAction = {
                "label": "$(refresh) * Refresh list",
                "description": "Expected Workspace is not appearing.",
                "sortKey": "09999", // last item
                "action": { "refresh": true },
            };
            captions.push(caption);

            let selectedItem: QuickPickItemWithAction = await showSelectOneQuickPick(captions, title);

            if (!selectedItem) {
                return undefined;
            }
            if (selectedItem.action.refresh) {
                refresh = true;
                continue SELECT_OR_REFRESH;
            } else {
                workspaceIdFilter = selectedItem.action.filterWorkspaceId;
                return {
                    "workspaceInfo": workspaceInfo,
                    "selectedWorkspaceInfo": selectedItem.action.wsInfo,
                };
            }
        } else {
            // Only 1
            return {
                "workspaceInfo": workspaceInfo,
                selectedWorkspaceInfo: workspaceInfo[0],
            };
        }
    } while (true);
}
