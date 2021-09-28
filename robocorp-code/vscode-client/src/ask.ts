import { QuickPickItem, window } from "vscode";

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
    message: string
): Promise<QuickPickItemWithAction> {
    let selectedItem: QuickPickItemWithAction = await window.showQuickPick(items, {
        "canPickMany": false,
        "placeHolder": message,
        "ignoreFocusOut": true,
    });
    return selectedItem;
}

export async function showSelectOneStrQuickPick(items: string[], message: string): Promise<string> {
    let selectedItem: string = await window.showQuickPick(items, {
        "canPickMany": false,
        "placeHolder": message,
        "ignoreFocusOut": true,
    });
    return selectedItem;
}
