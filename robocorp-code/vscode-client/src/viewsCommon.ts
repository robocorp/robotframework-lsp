import * as path from "path";
import * as vscode from "vscode";
import { TREE_VIEW_ROBOCORP_LOCATORS_TREE, TREE_VIEW_ROBOCORP_ROBOTS_TREE } from "./robocorpViews";

/**
 * Note: if type is error|info the name is the message to be shown.
 */
export interface LocatorEntry {
    name: string;
    line: number;
    column: number;
    type: string; // "browser", "image", "coordinate", "error", "info",...
    filePath: string;
}

export enum RobotEntryType {
    Robot,
    Task,
}

export interface CloudEntry {
    label: string;
    iconPath?: string;
    command?: vscode.Command;
    children?: CloudEntry[];
    viewItemContextValue?: string;
}

export interface RobotEntry {
    label: string;
    uri: vscode.Uri;
    robot: LocalRobotMetadataInfo;
    taskName?: string;
    iconPath: string;
    type: RobotEntryType;
}

export interface FSEntry {
    name: string;
    isDirectory: boolean;
    filePath: string;
}

export let treeViewIdToTreeView: Map<string, vscode.TreeView<any>> = new Map();
export let treeViewIdToTreeDataProvider: Map<string, vscode.TreeDataProvider<any>> = new Map();

export function getSingleTreeSelection(
    treeId: string,
    noSelectionMessage?: string,
    moreThanOneSelectionMessage?: string
) {
    const robotsTree = treeViewIdToTreeView.get(treeId);
    if (!robotsTree || robotsTree.selection.length == 0) {
        if (noSelectionMessage) {
            vscode.window.showWarningMessage(noSelectionMessage);
        }
        return undefined;
    }

    if (robotsTree.selection.length > 1) {
        if (moreThanOneSelectionMessage) {
            vscode.window.showWarningMessage(moreThanOneSelectionMessage);
        }
        return undefined;
    }

    let element = robotsTree.selection[0];
    return element;
}

/**
 * Returns the selected robot or undefined if there are no robots or if more than one robot is selected.
 *
 * If the messages are passed as a parameter, a warning is shown with that message if the selection is invalid.
 */
export function getSelectedRobot(
    noSelectionMessage?: string,
    moreThanOneSelectionMessage?: string
): RobotEntry | undefined {
    return getSingleTreeSelection(TREE_VIEW_ROBOCORP_ROBOTS_TREE, noSelectionMessage, moreThanOneSelectionMessage);
}

export function getSelectedLocator(
    noSelectionMessage?: string,
    moreThanOneSelectionMessage?: string
): LocatorEntry | undefined {
    return getSingleTreeSelection(TREE_VIEW_ROBOCORP_LOCATORS_TREE, noSelectionMessage, moreThanOneSelectionMessage);
}

export function basename(s) {
    return s.split("\\").pop().split("/").pop();
}

export const debounce = (func, wait) => {
    let timeout;

    return function wrapper(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };

        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};
