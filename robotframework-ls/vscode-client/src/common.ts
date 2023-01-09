import { Uri, workspace, WorkspaceFolder } from "vscode";
import { OUTPUT_CHANNEL } from "./channel";

export const debounce = (func, wait) => {
    let timeout: NodeJS.Timeout;

    return function wrapper(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };

        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

export function getWorkspaceFolderForUriAndShowInfoIfNotFound(uri: Uri): WorkspaceFolder | undefined {
    const workspaceFolder = workspace.getWorkspaceFolder(uri);
    if (workspaceFolder === undefined) {
        const folders: string[] = [];
        for (let ws of workspace.workspaceFolders) {
            folders.push(ws.uri.toString());
        }
        OUTPUT_CHANNEL.appendLine(`${uri} is not found as being inside any workspace folder (${folders.join(", ")}).`);
    }
    return workspaceFolder;
}
