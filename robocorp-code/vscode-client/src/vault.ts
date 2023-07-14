import * as roboCommands from "./robocorpCommands";
import * as vscode from "vscode";
import { cloudLogin } from "./activities";
import { selectWorkspace } from "./ask";
import { feedback } from "./rcc";
import { ActionResult } from "./protocols";

export async function connectWorkspace(checkLogin: boolean = true) {
    if (checkLogin) {
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
    }

    const workspaceSelection = await selectWorkspace(
        "Please select Workspace to enable access the related vault secrets and storage",
        false
    );
    if (workspaceSelection === undefined) {
        return;
    }
    let setWorkspaceResult: ActionResult<boolean> = await vscode.commands.executeCommand(
        roboCommands.ROBOCORP_SET_CONNECTED_VAULT_WORKSPACE_INTERNAL,
        {
            "workspaceId": workspaceSelection.selectedWorkspaceInfo.workspaceId,
            "organizationName": workspaceSelection.selectedWorkspaceInfo.organizationName,
            "workspaceName": workspaceSelection.selectedWorkspaceInfo.workspaceName,
        }
    );
    if (!setWorkspaceResult) {
        vscode.window.showInformationMessage("Error connecting to workspace.");
        return;
    }
    if (!setWorkspaceResult.success) {
        vscode.window.showInformationMessage("Error connecting to workspace: " + setWorkspaceResult.message);
        return;
    }
    feedback("vscode.vault", "connected");
    vscode.window.showInformationMessage("Connected to workspace.");
}

export async function disconnectWorkspace() {
    let setWorkspaceResult: ActionResult<boolean> = await vscode.commands.executeCommand(
        roboCommands.ROBOCORP_SET_CONNECTED_VAULT_WORKSPACE_INTERNAL,
        {
            "workspaceId": null,
        }
    );
    if (!setWorkspaceResult) {
        vscode.window.showInformationMessage("Error disconnecting from workspace.");
        return;
    }
    if (!setWorkspaceResult.success) {
        vscode.window.showInformationMessage("Error disconnecting from workspace: " + setWorkspaceResult.message);
        return;
    }
    feedback("vscode.vault", "disconnected");
    vscode.window.showInformationMessage("Disconnected from workspace.");
}
