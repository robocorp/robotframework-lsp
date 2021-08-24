import * as vscode from "vscode";
import { getSelectedLocator, LocatorEntry } from './viewsCommon';

export async function copySelectedToClipboard(locator?: LocatorEntry) {
    let locatorSelected: LocatorEntry | undefined = locator || getSelectedLocator();
    if (locatorSelected) {
        vscode.env.clipboard.writeText(locatorSelected.name);
    }
}
