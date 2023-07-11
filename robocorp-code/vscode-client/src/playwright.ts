import { ActionResult, LocalRobotMetadataInfo } from "./protocols";
import { RobotEntry, getSelectedRobot } from "./viewsCommon";
import { listAndAskRobotSelection } from "./activities";
import { OUTPUT_CHANNEL, logError } from "./channel";
import { commands, ProgressLocation, window } from "vscode";
import { ROBOCORP_OPEN_PLAYWRIGHT_RECORDER_INTERNAL } from "./robocorpCommands";

const logCleanLine = (s: string) => {
    return s.replace(/(?:\r\n|\r|\n)/g, "\n  i> ");
};

const logAppend = (s: string) => {
    OUTPUT_CHANNEL.appendLine(logCleanLine(s));
};

export async function openPlaywrightRecorder(): Promise<void> {
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
                "target_robot": robot,
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
