import * as roboCommands from './robocorpCommands';
import {
    commands,
    env,
    window,
    MessageOptions,
} from "vscode";
import { listAndAskRobotSelection } from './activities'
import { getSelectedLocator, getSelectedRobot, LocatorEntry } from './viewsCommon';
import { OUTPUT_CHANNEL } from './channel';


export async function copySelectedToClipboard(locator?: LocatorEntry) {
    let locatorSelected: LocatorEntry | undefined = locator || getSelectedLocator();
    if (locatorSelected) {
        env.clipboard.writeText(locatorSelected.name);
    }
}

export async function removeLocator(locator?: LocatorEntry) {
    // Confirmation dialog button texts
    const DELETE = 'Delete';
    let locatorSelected: LocatorEntry | undefined = locator || getSelectedLocator();
    if (!locatorSelected) {
        OUTPUT_CHANNEL.appendLine("Warning: Trying to delete locator when there is no locator selected")
        return;
    }
    let robot: LocalRobotMetadataInfo | undefined = getSelectedRobot('Please select a robot first.')?.robot;
    if (!robot) {
        // Ask for the robot to be used and then show dialog with the options.
        robot = await listAndAskRobotSelection(
          'Please select the Robot where the locator should be removed.',
          'Unable to remove locator (no Robot detected in the Workspace).'
        );
        if (!robot) {
            OUTPUT_CHANNEL.appendLine("Warning: Trying to delete locator when there is no robot selected")
            return;
        }
    }
    const result = await window.showWarningMessage(
      `Are you sure you want to delete the locator "${locatorSelected?.name}"?`,
      {'modal': true},
      DELETE,
    );
    if (result === DELETE) {
        const actionResult: ActionResult = await commands.executeCommand(roboCommands.ROBOCORP_REMOVE_LOCATOR_FROM_JSON_INTERNAL, {
            robotYaml: robot.filePath,
            name: locatorSelected?.name,
        });
        if (actionResult.success) OUTPUT_CHANNEL.appendLine(`Locator "${locatorSelected?.name} removed successfully`);
        else OUTPUT_CHANNEL.appendLine(`Unable to remove Locator "${locatorSelected?.name}, because of:\n${actionResult.message}`);
    }
}
