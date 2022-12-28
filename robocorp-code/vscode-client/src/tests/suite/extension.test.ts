import * as assert from "assert";
import * as path from "path";
import * as vscode from "vscode";
import { WorkspaceFolder } from "vscode";
import { ActionResult, LocalRobotMetadataInfo } from "../../protocols";
import { ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL } from "../../robocorpCommands";
import { sleep } from "../../time";

const testFolderLocation = "/resources/";

suite("Robocorp Code Extension Test Suite", () => {
    vscode.window.showInformationMessage("Start all tests.");

    test("Test that robots can be listed", async () => {
        // i.e.: Jus check that we're able to get the contents.
        let workspaceFolders: ReadonlyArray<WorkspaceFolder> = vscode.workspace.workspaceFolders;
        assert.strictEqual(workspaceFolders.length, 1);

        let actionResult: ActionResult<LocalRobotMetadataInfo[]>;
        actionResult = await vscode.commands.executeCommand(ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL);
        assert.strictEqual(actionResult.success, true);
        let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;
        // Check that we're able to load at least one robot.
        assert.ok(robotsInfo.length >= 1);
    });
});
