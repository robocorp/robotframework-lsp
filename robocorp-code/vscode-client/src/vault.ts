import * as roboCommands from "./robocorpCommands";
import * as vscode from "vscode";
import { cloudLogin } from "./activities";
import { selectWorkspace } from "./ask";

export async function connectVault() {
    let isLoginNeededActionResult: ActionResult<boolean> = await vscode.commands.executeCommand(
        roboCommands.ROBOCORP_IS_LOGIN_NEEDED_INTERNAL
    );
    if (!isLoginNeededActionResult) {
        vscode.window.showInformationMessage("Error getting if login is needed.");
        return;
    }

    if (isLoginNeededActionResult.result) {
        let loggedIn: boolean = await cloudLogin();
        if (!loggedIn) {
            return;
        }
    }

    const workspaceSelection = await selectWorkspace(
        "Please provide the workspace to connect the online Vault secrets",
        false
    );
    if (workspaceSelection === undefined) {
        return;
    }
    let setVaultResult: ActionResult<boolean> = await vscode.commands.executeCommand(
        roboCommands.ROBOCORP_SET_CONNECTED_VAULT_WORKSPACE_INTERNAL,
        {
            "workspaceId": workspaceSelection.selectedWorkspaceInfo.workspaceId,
            "organizationName": workspaceSelection.selectedWorkspaceInfo.organizationName,
            "workspaceName": workspaceSelection.selectedWorkspaceInfo.workspaceName,
        }
    );
    if (!setVaultResult) {
        vscode.window.showInformationMessage("Error connecting to vault.");
        return;
    }
    if (!setVaultResult.success) {
        vscode.window.showInformationMessage("Error connecting to vault: " + setVaultResult.message);
        return;
    }
    vscode.window.showInformationMessage("Connected to vault.");
}

export async function disconnectVault() {
    let setVaultResult: ActionResult<boolean> = await vscode.commands.executeCommand(
        roboCommands.ROBOCORP_SET_CONNECTED_VAULT_WORKSPACE_INTERNAL,
        {
            "workspaceId": null,
        }
    );
    if (!setVaultResult) {
        vscode.window.showInformationMessage("Error disconnecting from vault.");
        return;
    }
    if (!setVaultResult.success) {
        vscode.window.showInformationMessage("Error disconnecting from vault: " + setVaultResult.message);
        return;
    }
    vscode.window.showInformationMessage("Disconnected from vault.");
}
