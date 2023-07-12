import { ActionResult, LocalRobotMetadataInfo } from "./protocols";
import { RobotEntry, getSelectedRobot } from "./viewsCommon";
import { listAndAskRobotSelection } from "./activities";
import { logError } from "./channel";
import { commands, ProgressLocation, Uri, window } from "vscode";
import { ROBOCORP_OPEN_PLAYWRIGHT_RECORDER_INTERNAL } from "./robocorpCommands";

export async function openPlaywrightRecorder(useTreeSelected: boolean = false): Promise<void> {
    let currentUri: Uri | undefined = undefined;
    if (!useTreeSelected && window.activeTextEditor && window.activeTextEditor.document) {
        currentUri = window.activeTextEditor.document.uri;
    }

    if (!currentUri) {
        // User doesn't have a current editor opened, get from the tree
        // selection.
        let selectedEntry: RobotEntry = getSelectedRobot();
        let robot: LocalRobotMetadataInfo | undefined = selectedEntry?.robot;
        if (robot === undefined) {
            // Ask for the robot to be used and then show dialog with the options.
            robot = await listAndAskRobotSelection(
                "Please select the Robot where the locators should be saved.",
                "Unable to open Inspector (no Robot detected in the Workspace)."
            );
            if (!robot) {
                return;
            }
        }
        currentUri = Uri.file(robot.filePath);
    }

    if (!currentUri) {
        window.showErrorMessage("Unable to get selection for recording with playwright.");
        return;
    }

    let resolveProgress = undefined;
    window.withProgress(
        {
            location: ProgressLocation.Notification,
            title: "Robocorp",
            cancellable: false,
        },
        (progress) => {
            progress.report({ message: "Opening Playwright Recorder..." });
            return new Promise<void>((resolve) => {
                resolveProgress = resolve;
            });
        }
    );

    try {
        const actionResult: ActionResult<any> = await commands.executeCommand(
            ROBOCORP_OPEN_PLAYWRIGHT_RECORDER_INTERNAL,
            {
                "target_robot_uri": currentUri.toString(),
            }
        );
        if (!actionResult.success) {
            resolveProgress();
            await window.showErrorMessage(actionResult.message);
        }
    } catch (error) {
        logError("Error resolving interpreter:", error, "ACT_RESOLVE_INTERPRETER");
    } finally {
        resolveProgress();
    }
}
