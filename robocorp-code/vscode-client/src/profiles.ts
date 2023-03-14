/**
 * Profiles actions we're interested in:
 *
 * rcc.exe config import -f <path to profile.yaml>
 * -- the name of the profile is in the yaml, in the name field
 *    and the description in the description field.
 *
 * rcc.exe config switch -p <profile name>
 *
 * rcc.exe config switch -j
 * -- lists the current profile and the available ones.
 */
import { commands, Uri, window } from "vscode";
import { QuickPickItemWithAction, showSelectOneQuickPick } from "./ask";
import { ActionResult } from "./protocols";
import {
    ROBOCORP_PROFILE_IMPORT_INTERNAL,
    ROBOCORP_PROFILE_LIST_INTERNAL,
    ROBOCORP_PROFILE_SWITCH_INTERNAL,
} from "./robocorpCommands";

async function selectProfileFile(): Promise<Uri | undefined> {
    let uris: Uri[] = await window.showOpenDialog({
        "canSelectFolders": false,
        "canSelectFiles": true,
        "canSelectMany": false,
        "openLabel": `Select profile to import`,
    });
    if (uris && uris.length > 0) {
        return uris[0];
    }
    return undefined;
}

export async function profileImport() {
    const profileUri: Uri | undefined = await selectProfileFile();
    if (profileUri !== undefined) {
        const actionResult: ActionResult<any> = await commands.executeCommand(ROBOCORP_PROFILE_IMPORT_INTERNAL, {
            "profileUri": profileUri.toString(),
        });

        if (!actionResult.success) {
            await window.showErrorMessage(actionResult.message);
            return;
        }

        const profileName = actionResult.result["name"];
        if (profileName) {
            let accept = await window.showInformationMessage(
                `Profile imported. Do you want to switch to the imported profile (${profileName})?`,
                { "modal": true },
                "Yes",
                "No"
            );
            if (accept === "Yes") {
                await profileSwitchInternal(profileName);
            }
        }
    }
}

async function profileSwitchInternal(profileName: string) {
    const actionResult: ActionResult<any> = await commands.executeCommand(ROBOCORP_PROFILE_SWITCH_INTERNAL, {
        "profileName": profileName,
    });
    if (!actionResult) {
        await window.showErrorMessage("Unexpected error switching profile.");
        return;
    }
    if (!actionResult.success) {
        await window.showErrorMessage(actionResult.message);
        return;
    }
    if (profileName === "<remove-current-back-to-defaults>") {
        profileName = "Default";
    }
    window.showInformationMessage(profileName + " is now the current profile.");
}

export async function profileSwitch() {
    const actionResult: ActionResult<any> = await commands.executeCommand(ROBOCORP_PROFILE_LIST_INTERNAL);

    if (!actionResult.success) {
        await window.showErrorMessage(actionResult.message);
        return;
    }

    const currentProfile = actionResult.result["current"];
    const profiles = actionResult.result["profiles"];
    const items = [];
    for (const [key, val] of Object.entries(profiles)) {
        let item: QuickPickItemWithAction = {
            "label": key,
            "description": `${val}`,
            "action": key,
        };
        items.push(item);
    }
    items.push({
        "label": "Unset current profile",
        "description": "Switch back to the 'default' profile.",
        "action": "<remove-current-back-to-defaults>",
    });
    let selected = await showSelectOneQuickPick(
        items,
        `Select profile to switch to (current profile: ${currentProfile}).`
    );
    if (selected) {
        await profileSwitchInternal(selected.action);
    }
}
