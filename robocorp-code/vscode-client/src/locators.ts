import { env } from "vscode";
import { getSelectedLocator, LocatorEntry } from './viewsCommon';

export async function copySelectedToClipboard() {
    let locatorSelected: LocatorEntry | undefined = getSelectedLocator();
    if (locatorSelected) {
        env.clipboard.writeText(locatorSelected.name);
    }
}
