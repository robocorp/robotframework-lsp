import * as roboCommands from './robocorpCommands';
import { commands, window, env } from "vscode";
import { askRobotSelection, listAndAskRobotSelection } from "./activities";
import { QuickPickItemWithAction, showSelectOneQuickPick, showSelectOneStrQuickPick } from './ask';
import { getSelectedLocator, getSelectedRobot, LocatorEntry } from './viewsCommon';
import { OUTPUT_CHANNEL } from './channel';


let LAST_URL: string = undefined;


export async function newLocatorUI(robotYaml?: string) {
    if (!robotYaml) {
        // Ask for the robot to be used and then show dialog with the options.
        let robot: LocalRobotMetadataInfo = await listAndAskRobotSelection(
            'Please select the Robot where the locators should be saved.',
            'Unable to create locator (no Robot detected in the Workspace).'
        );
        if (!robot) {
            return;
        }
        robotYaml = robot.filePath;
    }

    let items: QuickPickItemWithAction[] = [{
        'label': 'Browser Locator',
        'description': 'Select element in browser to create a Locator',
        'action': 'browser'
    },
    {
        'label': 'Image Locator',
        'description': 'Create Image locator from a screen region.',
        'action': 'image'
    }];
    let selectedItem: QuickPickItemWithAction = await showSelectOneQuickPick(
        items,
        "Select locator to create"
    );
    if (!selectedItem) {
        return;
    }

    if (selectedItem.action == 'browser') {
        await newBrowserLocatorUI(robotYaml);
    } else if (selectedItem.action == 'image') {
        await newImageLocatorUI(robotYaml);
    } else {
        throw Error('Unexpected action: ' + selectedItem.action);
    }
}

async function newImageLocatorUI(robotYaml: string) {
    let msg = "Select action";
    while (true) {
        let items: QuickPickItemWithAction[] = [{
            'label': 'Create Image Locator from screen region',
            'description': 'Please arrange the windows prior to activating this option',
            'action': 'pick'
        },
        {
            'label': 'Cancel',
            'description': 'Stops Locator creation',
            'action': 'stop'
        }];
        let selectedItem: QuickPickItemWithAction = await showSelectOneQuickPick(
            items,
            msg
        );
        if (!selectedItem || selectedItem.action == 'stop') {
            return;
        }
        await pickImageLocator(robotYaml);
        msg = 'Locator created. Do you want to create another one?';
    }
}


async function newBrowserLocatorUI(robotYaml: string) {
    startBrowserLocator(robotYaml);
    let msg = "When browser is opened, enter the URL and when ready select 'Create Browser Locator from Pick'.";
    while (true) {
        let items: QuickPickItemWithAction[] = [{
            'label': 'Create Browser Locator from Pick',
            'description': 'Select element in browser to create a Locator',
            'action': 'pick'
        },
        {
            'label': 'Cancel',
            'description': 'Closes Browser and stops Locator creation',
            'action': 'stop'
        }];
        let selectedItem: QuickPickItemWithAction = await showSelectOneQuickPick(
            items,
            msg
        );
        if (!selectedItem || selectedItem.action == 'stop') {
            await commands.executeCommand(roboCommands.ROBOCORP_STOP_BROWSER_LOCATOR);
            return;
        }
        await pickBrowserLocator();
        msg = 'Locator created. Do you want to create another one or close the browser?'
    }
}

export async function copySelectedToClipboard() {
    let locatorSelected: LocatorEntry | undefined = getSelectedLocator();
    if (locatorSelected) {
        env.clipboard.writeText(locatorSelected.name);
    }
}

export async function newLocatorUITreeInternal(robotYaml?: string) {
    // Same as newLocatorUI but we'll use the robot passed as a parameter or
    // get the selected robot from the robots tree.
    if (!robotYaml) {
        let robotEntry = getSelectedRobot(
            "Unable to create locator (Robot not selected in Robots Tree).",
            "Unable to create locator -- only 1 Robot must be selected.");
        if (!robotEntry) {
            return;
        }

        robotYaml = robotEntry.robot.filePath;
    }
    if (!robotYaml) {
        window.showErrorMessage('robotYaml not available to create locator.')
    }
    // For now we can only deal with the Browser Locator...
    // let s = showSelectOneStrQuickPick(['Browser Locator'], 'Select locator to create');
    newLocatorUI(robotYaml);
}

export async function pickBrowserLocator() {
    let pickResult: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCORP_CREATE_LOCATOR_FROM_BROWSER_PICK_INTERNAL
    );

    if (pickResult.success) {
        window.showInformationMessage("Created locator: " + pickResult.result['name']);
    } else {
        OUTPUT_CHANNEL.appendLine(pickResult.message);
        window.showErrorMessage(pickResult.message);
    }
}

export async function pickImageLocator(robotYaml?: string) {
    if (!robotYaml) {
        let robot: LocalRobotMetadataInfo = await listAndAskRobotSelection(
            'Please select the Robot where the locators should be saved.',
            'Unable to create image locator (no Robot detected in the Workspace).'
        );
        if (!robot) {
            return;
        }
        robotYaml = robot.filePath;
    }

    let pickResult: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCORP_CREATE_LOCATOR_FROM_SCREEN_REGION_INTERNAL, { 'robotYaml': robotYaml }
    );

    if (pickResult.success) {
        window.showInformationMessage("Created locator: " + pickResult.result['name']);
    } else {
        OUTPUT_CHANNEL.appendLine(pickResult.message);
        window.showErrorMessage(pickResult.message);
    }
}

export async function startBrowserLocator(robotYaml?: string) {
    if (!robotYaml) {
        let robot: LocalRobotMetadataInfo = await listAndAskRobotSelection(
            'Please select the Robot where the locators should be saved.',
            'Unable to start browser locator (no Robot detected in the Workspace).'
        );
        if (!robot) {
            return;
        }
        robotYaml = robot.filePath;
    }

    let actionResultCreateLocator: ActionResult = await commands.executeCommand(
        roboCommands.ROBOCORP_START_BROWSER_LOCATOR_INTERNAL, { 'robotYaml': robotYaml }
    );

    if (actionResultCreateLocator.success) {
        window.showInformationMessage("Started browser to create locators. Please use the 'Robocorp: Create Locator from Browser Pick' command to actually create a locator.");
    } else {
        OUTPUT_CHANNEL.appendLine(actionResultCreateLocator.message);
        window.showErrorMessage(actionResultCreateLocator.message);
    }
}