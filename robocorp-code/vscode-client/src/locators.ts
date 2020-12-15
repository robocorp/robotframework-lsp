import * as roboCommands from './robocorpCommands';
import { commands, window } from "vscode";
import { askRobotSelection } from "./activities";

let LAST_URL: string = undefined;

export async function pickBrowserLocator() {
    let pickResult: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCORP_CREATE_LOCATOR_FROM_BROWSER_PICK_INTERNAL
    );

    if (pickResult.success) {
        window.showInformationMessage("Created locator: " + pickResult.result['name']);
    } else {
        window.showErrorMessage(pickResult.message);
    }

}

export async function startBrowserLocator() {
    let actionResult: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
    );

    if (!actionResult.success) {
        window.showInformationMessage('Error listing robots: ' + actionResult.message);
        return;
    }
    let robotsInfo: LocalRobotMetadataInfo[] = actionResult.result;

    if (!robotsInfo || robotsInfo.length == 0) {
        window.showInformationMessage('Unable to start browser locator (no Robot detected in the Workspace).');
        return;
    }

    let robot: LocalRobotMetadataInfo = await askRobotSelection(robotsInfo, 'Please select the Robot where the locators should be saved.');
    if (!robot) {
        return;
    }

    let actionResultCreateLocator: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCORP_START_BROWSER_LOCATOR_INTERNAL, { 'robotYaml': robot.filePath }
    );

    if (actionResultCreateLocator.success) {
        window.showInformationMessage("Started browser to create locators. Please use the 'Robocorp: Create Locator from Browser Pick' command to actually create a locator.");
    } else {
        window.showErrorMessage(actionResultCreateLocator.message);
    }
}