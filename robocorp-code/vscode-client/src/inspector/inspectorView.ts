/**
 * Interesting docs related to webviews:
 * https://code.visualstudio.com/api/extension-guides/webview
 */
import path = require("path");
import { readFileSync } from "fs";

import * as vscode from "vscode";

import { getExtensionRelativeFile, verifyFileExists } from "../files";
import { OUTPUT_CHANNEL } from "../channel";
import { getSelectedRobot } from "../viewsCommon";
import { BrowserLocator, LocatorsMap } from "./types";
import { IApps, IEventMessage, IMessage, IMessageType, IResponseMessage } from "./protocols";
import { langServer } from "../extension";
import { ActionResult, LocalRobotMetadataInfo } from "../protocols";
import { ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL } from "../robocorpCommands";

export async function showInspectorUI(context: vscode.ExtensionContext) {
    const panel = vscode.window.createWebviewPanel(
        "robocorpCodeInspector",
        "Robocorp Inspector",
        vscode.ViewColumn.Beside,
        {
            enableScripts: true,
            retainContextWhenHidden: true,
        }
    );

    const robot = getSelectedRobot();
    let directory = undefined;
    let locatorJson = undefined;
    if (robot) {
        directory = robot.robot.directory;
    } else {
        let actionResult: ActionResult<LocalRobotMetadataInfo[]> = await vscode.commands.executeCommand(
            ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL
        );
        if (actionResult.success) {
            if (actionResult.result.length === 1) {
                directory = actionResult.result[0].directory;
            }
        }
    }
    if (directory) {
        locatorJson = path.join(directory, "locators.json");
    }

    let locatorsMap = {};
    if (locatorJson) {
        if (verifyFileExists(locatorJson, false)) {
            let doc = await vscode.workspace.openTextDocument(vscode.Uri.file(locatorJson));
            locatorsMap = JSON.parse(doc.getText()) as LocatorsMap;
        }
    }
    panel.webview.html = getWebviewContent(locatorsMap);

    context.subscriptions.push(
        langServer.onNotification("$/webPick", (values) => {
            const pickedLocator: BrowserLocator = JSON.stringify(values) as unknown as BrowserLocator;
            OUTPUT_CHANNEL.appendLine(`> Receiving: picked.element: ${pickedLocator}`);
            const response: IEventMessage = {
                id: Date.now(),
                type: IMessageType.EVENT,
                event: {
                    type: "pickedLocator",
                    status: "success",
                    data: pickedLocator,
                },
            };
            // this is an event - postMessage will update the useLocator hook
            panel.webview.postMessage(response);
        })
    );

    panel.onDidDispose(() => {
        langServer.sendRequest("webInspectorCloseBrowser", {});
    });

    panel.webview.onDidReceiveMessage(
        async (message: IMessage) => {
            OUTPUT_CHANNEL.appendLine(`incoming.message: ${JSON.stringify(message)}`);
            switch (message.type) {
                case IMessageType.REQUEST:
                    const command = message.command;
                    if (command["type"] === "getLocators") {
                        OUTPUT_CHANNEL.appendLine(`> Requesting: Get Locators`);
                        const response: IResponseMessage = await langServer.sendRequest("loadRobotLocatorContents", {
                            message: message,
                            directory: directory,
                        });
                        OUTPUT_CHANNEL.appendLine(`> Requesting: Locators JSON: ${JSON.stringify(response)}`);
                        // this is a response - postMessage will update the broker hook
                        panel.webview.postMessage(response);
                    }
                    if (message.app === IApps.WEB_PICKER) {
                        if (command["type"] === "startPicking") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Open Browser`);
                            await langServer.sendRequest("webInspectorOpenBrowser");
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Start Picker`);
                            await langServer.sendRequest("webInspectorStartPick");
                        }
                        if (command["type"] === "stopPicking") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Stop Picker`);
                            await langServer.sendRequest("webInspectorStopPick");
                        }
                        if (command["type"] === "save") {
                            OUTPUT_CHANNEL.appendLine(
                                `> Requesting: Saving Locator: ${JSON.stringify(command["locator"])}`
                            );
                            const response: IResponseMessage = await langServer.sendRequest("webInspectorSaveLocator", {
                                message: message,
                                directory: directory,
                            });
                            OUTPUT_CHANNEL.appendLine(
                                `> Requesting: Response from saving locator: ${JSON.stringify(response)}`
                            );
                            // this is a response - postMessage will update the broker hook
                            panel.webview.postMessage(response);
                        }
                    }
                    return;
                case IMessageType.RESPONSE:
                    return;
                case IMessageType.EVENT:
                    return;
                default:
                    return;
            }
        },
        undefined,
        context.subscriptions
    );
}

function getWebviewContent(jsonData: LocatorsMap): string {
    const jsonDataStr = JSON.stringify(jsonData, null, 4);
    const templateFile = getExtensionRelativeFile("../../vscode-client/templates/inspector.html", true);
    const data = readFileSync(templateFile, "utf8");

    const start = '<script id="locatorsJSON" type="application/json">';
    const startI = data.indexOf(start) + start.length;
    const end = "</script>";
    const endI = data.indexOf(end, startI);

    const ret: string = data.substring(0, startI) + jsonDataStr + data.substring(endI);
    return ret;
}
