import * as vscode from "vscode";
import { OUTPUT_CHANNEL } from "./channel";
import { InspectorType } from "./inspector";
import { ActionResult } from "./protocols";
import * as roboCommands from "./robocorpCommands";
import { getSelectedRobot, LocatorEntry, RobotEntry } from "./viewsCommon";

export class LocatorsTreeDataProvider
    implements vscode.TreeDataProvider<LocatorEntry | LocatorEntryNode | LocatorCreationNode>
{
    async getChildren(element?: LocatorEntry | LocatorEntryNode | LocatorCreationNode): Promise<any[]> {
        // i.e.: the contents of this tree depend on what's selected in the robots tree.
        const robotEntry: RobotEntry = getSelectedRobot();
        if (!robotEntry) {
            return [
                {
                    name: "<Waiting for Robot Selection...>",
                    type: "info",
                    line: 0,
                    column: 0,
                    filePath: undefined,
                },
            ];
        }

        if (!element) {
            // Collect the basic structure and create tree from it.
            // Afterwards, just return element.children for any subsequent request.
            let actionResult: ActionResult<LocatorEntry[]> = await vscode.commands.executeCommand(
                roboCommands.ROBOCORP_GET_LOCATORS_JSON_INFO,
                { "robotYaml": robotEntry.robot.filePath }
            );
            if (!actionResult["success"]) {
                return [
                    {
                        name: actionResult.message,
                        type: "error",
                        line: 0,
                        column: 0,
                        filePath: robotEntry.robot.filePath,
                    },
                ];
            }
            return buildTree(actionResult["result"]);
        }
        if (element instanceof LocatorEntryNode) {
            return element.children;
        } else {
            // LocatorEntry has no children
            return [];
        }
    }
    getTreeItem(entry: LocatorEntry | LocatorEntryNode | LocatorCreationNode): vscode.TreeItem {
        if (entry instanceof LocatorCreationNode) {
            // Custom node to add a locator.
            const node = <LocatorEntryNode>entry;
            const treeItem = new vscode.TreeItem(node.caption);
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.None;
            treeItem.iconPath = new vscode.ThemeIcon("add");
            let commandName: string;
            if (node.locatorType === InspectorType.PlaywrightRecorder) {
                commandName = roboCommands.ROBOCORP_OPEN_PLAYWRIGHT_RECORDER;
                treeItem.command = {
                    "title": node.caption,
                    "command": commandName,
                    "arguments": [true],
                };
            } else {
                // Command: robocorp.newRobocorpInspectorBrowser
                // Command: robocorp.newRobocorpInspectorImage
                // Command: robocorp.newRobocorpInspectorWindows
                // Command: robocorp.newRobocorpInspectorWebRecorder
                commandName =
                    "robocorp.newRobocorpInspector" +
                    (node.locatorType.charAt(0).toUpperCase() + node.locatorType.substring(1)).replace("-r", "R");
                treeItem.command = {
                    "title": node.caption,
                    "command": commandName,
                    "arguments": [],
                };
            }

            if (node.tooltip) {
                treeItem.tooltip = node.tooltip;
            }
            return treeItem;
        }

        const type: string = entry instanceof LocatorEntryNode ? entry.locatorType : entry.type;
        // https://microsoft.github.io/vscode-codicons/dist/codicon.html
        let iconPath = "file-media";
        if (type === InspectorType.Browser) {
            iconPath = "globe";
        } else if (type === InspectorType.Image) {
            iconPath = "file-media";
        } else if (type === InspectorType.Windows) {
            iconPath = "multiple-windows";
        } else if (type === InspectorType.Java) {
            iconPath = "coffee";
        } else if (type === InspectorType.PlaywrightRecorder) {
            iconPath = "browser";
        } else if (type === "error" || type === "info") {
            iconPath = "error";
        } else {
            OUTPUT_CHANNEL.appendLine("No custom icon for: " + type);
        }

        if (entry instanceof LocatorEntryNode) {
            // Node which contains locators as children.
            const node = <LocatorEntryNode>entry;
            const treeItem = new vscode.TreeItem(node.caption);
            treeItem.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
            treeItem.iconPath = new vscode.ThemeIcon(iconPath);
            if (entry.locatorType === InspectorType.Browser) {
                treeItem.contextValue = "newBrowserLocator";
                treeItem.tooltip = "Browser locators saved for future references";
            } else if (entry.locatorType === InspectorType.Image) {
                treeItem.contextValue = "newImageLocator";
            } else if (entry.locatorType === InspectorType.Java) {
                treeItem.contextValue = "newJavaLocator";
            } else if (entry.locatorType === InspectorType.Windows) {
                treeItem.contextValue = "newWindowsLocator";
            } else if (entry.locatorType === InspectorType.WebRecorder) {
                treeItem.contextValue = "newWebRecorder";
            }
            return treeItem;
        }

        const element = <LocatorEntry>entry;
        const treeItem = new vscode.TreeItem(element.name);

        // Only add context to actual locator items
        if (element.type !== "error") {
            treeItem.contextValue = "locatorEntry";
        }
        treeItem.iconPath = new vscode.ThemeIcon(iconPath);
        return treeItem;
    }
}

class LocatorEntryNode {
    children: any[] = []; // LocatorEntry and LocatorCreationNode entries mixed
    locatorType: string;
    caption: string;
    hasCreateNew: boolean;
    tooltip: string | undefined = undefined;

    constructor(locatorType: string, caption: string, hasCreateNew: boolean) {
        this.locatorType = locatorType;
        this.caption = caption;
        this.hasCreateNew = hasCreateNew;
    }

    addCreateNewElement() {
        if (this.hasCreateNew) {
            if (this.locatorType === InspectorType.PlaywrightRecorder) {
                this.children.push(
                    new LocatorCreationNode(
                        this.locatorType,
                        "Playwright Recorder (Python) ...",
                        "A recorder which records browser actions to be used in Python with the `playwright` library."
                    )
                );
                return;
            }
            this.children.push(
                new LocatorCreationNode(
                    this.locatorType,
                    "New " + this.caption + " Locator ...",
                    `Select and store in \`locators.json\` a locator to be used with the ${this.caption} library.`
                )
            );
        }
    }
}

class LocatorCreationNode {
    locatorType: string;
    caption: string;
    tooltip: string | undefined;

    constructor(locatorType: string, caption: string, tooltip: string | undefined = undefined) {
        this.locatorType = locatorType;
        this.caption = caption;
        this.tooltip = tooltip;
    }
}

function buildTree(entries: LocatorEntry[]): any[] {
    // Roots may mix LocatorEntryNode along with LocatorEntry (if it's an error).
    const roots: any[] = [
        new LocatorEntryNode(InspectorType.Browser, "Web", true),
        new LocatorEntryNode(InspectorType.Windows, "Windows", true),
        new LocatorEntryNode(InspectorType.Image, "Image", true),
        new LocatorEntryNode(InspectorType.Java, "Java", true),
        new LocatorEntryNode(InspectorType.PlaywrightRecorder, "Playwright", true),
    ];
    const typeToElement = {};
    roots.forEach((element) => {
        typeToElement[element.locatorType] = element;
    });
    entries.forEach((element) => {
        const locatorType = element.type;
        if (locatorType === "error") {
            // Just put in the roots in this case.
            roots.push(element);
            return;
        }
        let node = typeToElement[locatorType];
        if (!node) {
            // Fallback if a new type is added which we weren't expecting.
            let caption = locatorType.charAt(0).toUpperCase() + locatorType.substring(1);
            node = new LocatorEntryNode(locatorType, caption, false);
            roots.push(node);
            typeToElement[locatorType] = node;
        }
        node.children.push(element);
    });

    roots.forEach((element) => {
        element.addCreateNewElement();
    });

    return roots;
}
