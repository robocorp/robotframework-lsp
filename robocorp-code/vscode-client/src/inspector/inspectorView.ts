/**
 * Interesting docs related to webviews:
 * https://code.visualstudio.com/api/extension-guides/webview
 */
import path = require("path");
import { readFileSync } from "fs";

import * as vscode from "vscode";

import { getExtensionRelativeFile, verifyFileExists } from "../files";
import { OUTPUT_CHANNEL, buildErrorStr, logError } from "../channel";
import { getSelectedRobot } from "../viewsCommon";
import { BrowserLocator, LocatorsMap, WindowsLocator } from "./types";
import {
    IApps,
    IEventMessage,
    IMessage,
    IMessageType,
    IRequestMessage,
    IResponseMessage,
    ResponseDataType,
} from "./protocols";
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
    panel.webview.html = getWebviewContent(directory, locatorsMap);

    // Web Inspector - Create listeners for BE (Python) messages
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
    context.subscriptions.push(
        langServer.onNotification("$/webInspectorState", (state) => {
            OUTPUT_CHANNEL.appendLine(`> Receiving: webInspectorState: ${JSON.stringify(state)}`);
        })
    );
    // Windows Inspector - Create listeners for BE (Python) messages
    context.subscriptions.push(
        langServer.onNotification("$/windowsPick", (values) => {
            const pickedLocator: WindowsLocator = JSON.stringify(values) as unknown as WindowsLocator;
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
        sendRequest("webInspectorCloseBrowser", {});
    });

    const buildProtocolResponseFromActionResponse = (
        message: IRequestMessage,
        actionResult: ActionResult<any>,
        dataType?: ResponseDataType
    ): IResponseMessage => {
        const response: IResponseMessage = {
            id: message.id,
            app: message.app,
            type: "response" as IMessageType.RESPONSE,
            status: actionResult.success ? "success" : "failure",
            message: actionResult.message,
            data:
                dataType && actionResult.result
                    ? {
                          type: dataType,
                          value: actionResult.result,
                      }
                    : undefined,
        };
        return response;
    };

    const sendRequest = async (requestName: string, args?: object): Promise<ActionResult<any>> => {
        try {
            if (args !== undefined) {
                return await langServer.sendRequest(requestName, args);
            } else {
                return await langServer.sendRequest(requestName);
            }
        } catch (error) {
            logError("Error on request: " + requestName, error, "INSPECTOR_VIEW_REQUEST_ERROR");
            // We always need a response even if an exception happens (so, build an ActionResult
            // from it).
            return { message: buildErrorStr(error), success: false, result: undefined };
        }
    };

    panel.webview.onDidReceiveMessage(
        async (message: IMessage) => {
            OUTPUT_CHANNEL.appendLine(`incoming.message: ${JSON.stringify(message)}`);
            switch (message.type) {
                case IMessageType.REQUEST:
                    const command = message.command;
                    if (command["type"] === "getLocators") {
                        const actionResult: ActionResult<LocatorsMap> = await sendRequest("loadRobotLocatorContents", {
                            directory: directory,
                        });
                        const response: IResponseMessage = buildProtocolResponseFromActionResponse(
                            message,
                            actionResult
                        );
                        response.data.type = "locatorsMap";
                        response.data.value = actionResult.result;
                    } else if (message.app === IApps.WEB_RECORDER) {
                        if (command["type"] === "startPicking") {
                            await sendRequest("webInspectorStartPick");
                        } else if (command["type"] === "stopPicking") {
                            await sendRequest("webInspectorStopPick");
                        } else if (command["type"] === "save") {
                            const locator = message["command"]["locator"];
                            const actionResult: ActionResult<any> = await sendRequest("webInspectorSaveLocator", {
                                locator: locator,
                                directory: directory,
                            });

                            panel.webview.postMessage(buildProtocolResponseFromActionResponse(message, actionResult));
                        }
                    } else if (message.app === IApps.LOCATORS_MANAGER) {
                        if (command["type"] === "delete") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Delete Locators: ${command["ids"]}`);
                            const actionResult: ActionResult<any> = await sendRequest("webInspectorDeleteLocators", {
                                directory: directory,
                                ids: command["ids"],
                            });
                            panel.webview.postMessage(buildProtocolResponseFromActionResponse(message, actionResult));
                        }
                    } else if (message.app === IApps.WINDOWS_RECORDER) {
                        if (command["type"] === "startPicking") {
                            await sendRequest("windowsInspectorStartPick");
                        } else if (command["type"] === "stopPicking") {
                            await sendRequest("windowsInspectorStopPick");
                        } else if (command["type"] === "getAppWindows") {
                            const actionResult: ActionResult<any> = await sendRequest("windowsInspectorListWindows");
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "winApps")
                            );
                        } else if (command["type"] === "setSelectedApp") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Set Selected App: ${JSON.stringify(command)}`);
                            const actionResult: ActionResult<any> = await sendRequest(
                                "windowsInspectorSetWindowLocator",
                                { locator: `handle:${command["handle"]}` }
                            );
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result)
                            );
                        } else if (command["type"] === "collectAppTree") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: collectAppTree: ${JSON.stringify(command)}`);
                            const actionResult: ActionResult<any> = await sendRequest("windowsInspectorCollectTree", {
                                locator: command["locator"],
                                search_depth: command["depth"] || 8,
                                search_strategy: command["strategy"] || "all",
                            });
                            OUTPUT_CHANNEL.appendLine(`> Requesting: result: ${JSON.stringify(actionResult)}`);
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "winAppTree")
                            );
                        } else if (command["type"] === "validateLocatorSyntax") {
                            OUTPUT_CHANNEL.appendLine(
                                `> Requesting: validateLocatorSyntax: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("windowsInspectorParseLocator", {
                                locator: command["locator"],
                            });
                            OUTPUT_CHANNEL.appendLine(`> Requesting: result: ${JSON.stringify(actionResult)}`);
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locator")
                            );
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

function getWebviewContent(directory: string, jsonData: LocatorsMap): string {
    const templateFile = getExtensionRelativeFile("../../vscode-client/templates/inspector.html", true);
    const data = readFileSync(templateFile, "utf8");

    const start = '<script id="locatorsJSON" type="application/json">';
    const startI = data.indexOf(start) + start.length;
    const end = "</script>";
    const endI = data.indexOf(end, startI);

    const jsonDataStr = JSON.stringify({ location: directory, data: jsonData }, null, 4);
    const ret: string = data.substring(0, startI) + jsonDataStr + data.substring(endI);
    return ret;
}
