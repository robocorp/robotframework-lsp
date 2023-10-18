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
import { IApps, IMessage, IMessageType, IResponseMessage } from "./protocols";
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
            const response: IResponseMessage = {
                id: Date.now(),
                type: IMessageType.RESPONSE,
                app: IApps.WEB_PICKER,
                status: "success",
                data: {
                    type: "locator",
                    data: pickedLocator,
                },
            };
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
                    if (message.app === IApps.WEB_PICKER) {
                        if (command["type"] === "startPicking") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Open Browser`);
                            const openBrowserResponse = await langServer.sendRequest("webInspectorOpenBrowser");
                            OUTPUT_CHANNEL.appendLine(`openBrowserResponse: ${JSON.stringify(openBrowserResponse)}`);
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Start Picker`);
                            const pickResponse = await langServer.sendRequest("webInspectorStartPick");
                            OUTPUT_CHANNEL.appendLine(`pickResponse: ${JSON.stringify(pickResponse)}`);
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
                                directory: directory,
                                message: message,
                            });

                            OUTPUT_CHANNEL.appendLine(
                                `> Requesting: Response from saving locator: ${JSON.stringify(response)}`
                            );
                            panel.webview.postMessage(response);
                        }
                        // const response: IResponseMessage = {
                        //     id: message.id,
                        //     app: message.app,
                        //     type: "response" as IMessageType.RESPONSE,
                        // };
                        // panel.webview.postMessage(response);
                    }
                    // OUTPUT_CHANNEL.appendLine(`request: ${JSON.stringify(message)}`);
                    // const response: IResponseMessage = {
                    //     id: message.id,
                    //     app: message.app,
                    //     type: "response" as IMessageType.RESPONSE,
                    //     data: {
                    //         type: "locator",
                    //         data: { type: "browser" as LocatorType.Browser, strategy: "css", value: "class" },
                    //     },
                    // };
                    // OUTPUT_CHANNEL.appendLine(`responding.in.3.seconds.with: ${JSON.stringify(response)}`);
                    // await sleep(3000);
                    // panel.webview.postMessage(response);
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
