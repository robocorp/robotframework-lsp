import * as vscode from "vscode";
import * as roboCommands from './robocorpCommands';
import { listAndAskRobotSelection } from './activities'
import { getSelectedLocator, getSelectedRobot, LocatorEntry } from './viewsCommon';
import { OUTPUT_CHANNEL } from './channel';


export async function copySelectedToClipboard(locator?: LocatorEntry) {
    let locatorSelected: LocatorEntry | undefined = locator || getSelectedLocator();
    if (locatorSelected) {
        vscode.env.clipboard.writeText(locatorSelected.name);
    }
}

export async function removeLocator(locator?: LocatorEntry) {
    let locatorSelected: LocatorEntry | undefined = locator || getSelectedLocator();
    let robot: LocalRobotMetadataInfo | undefined = getSelectedRobot('Please select a robot first.')?.robot;
    if (!robot) {
        // Ask for the robot to be used and then show dialog with the options.
        robot = await listAndAskRobotSelection(
          'Please select the Robot where the locator should be removed.',
          'Unable to remove locator (no Robot detected in the Workspace).'
        );
        if (!robot) return;
    }
    const actionResult: ActionResult = await vscode.commands.executeCommand(roboCommands.ROBOCORP_REMOVE_LOCATOR_FROM_JSON_INTERNAL, {
        robotYaml: robot.filePath,
        name: locatorSelected.name,
    });
    if (actionResult.success) OUTPUT_CHANNEL.appendLine(`Locator "${locatorSelected.name} removed successfully`);
    else OUTPUT_CHANNEL.appendLine(`Unable to remove Locator "${locatorSelected.name}, because of:\n${actionResult.message}`);
}
