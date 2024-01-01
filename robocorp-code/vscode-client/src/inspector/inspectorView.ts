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
import { BrowserLocator, LocatorsMap } from "./types";
import {
    BrowserState,
    IApps,
    IEventMessage,
    IMessage,
    IMessageType,
    IRequestMessage,
    IResponseMessage,
    ResponseDataType,
    WindowsAppTree,
} from "./protocols";
import { langServer } from "../extension";
import { ActionResult, LocalRobotMetadataInfo } from "../protocols";
import { ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL } from "../robocorpCommands";

let ROBOCORP_INSPECTOR_IS_OPENED = false;

export enum InspectorAppRoutes {
    LOCATORS_MANAGER = "/locators-manager/",
    WEB_INSPECTOR = "/web-inspector/",
    WINDOWS_INSPECTOR = "/windows-inspector/",
    JAVA_INSPECTOR = "/java-inspector/",
    IMAGE_INSPECTOR = "/image-inspector/",
}

export async function showInspectorUI(context: vscode.ExtensionContext, route?: InspectorAppRoutes) {
    if (ROBOCORP_INSPECTOR_IS_OPENED) {
        OUTPUT_CHANNEL.appendLine("# Robocorp Inspector is already opened! Thank you!");
        return;
    }
    ROBOCORP_INSPECTOR_IS_OPENED = true;

    const panel = vscode.window.createWebviewPanel(
        "robocorpCodeInspector",
        "Robocorp Inspector",
        vscode.ViewColumn.Active,
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
    panel.webview.html = getWebviewContent(directory, locatorsMap, route);

    // Web Inspector - Create listeners for BE (Python) messages
    context.subscriptions.push(
        langServer.onNotification("$/webPick", (values) => {
            const pickedLocator: BrowserLocator = JSON.stringify(values) as unknown as BrowserLocator;
            OUTPUT_CHANNEL.appendLine(`> Receiving: picked.element: ${pickedLocator}`);
            const response: IEventMessage = {
                id: "",
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
            const response: IEventMessage = {
                id: "",
                type: IMessageType.EVENT,
                event: {
                    type: "browserState",
                    status: "success",
                    data: state.state as BrowserState,
                },
            };
            // this is an event - postMessage will update the useLocator hook
            panel.webview.postMessage(response);
        })
    );
    context.subscriptions.push(
        langServer.onNotification("$/webURLChange", (url) => {
            OUTPUT_CHANNEL.appendLine(`> Receiving: webURLChange: ${JSON.stringify(url)}`);
            const response: IEventMessage = {
                id: "",
                type: IMessageType.EVENT,
                event: {
                    type: "urlChange",
                    status: "success",
                    data: url.url,
                },
            };
            // this is an event - postMessage will update the useLocator hook
            panel.webview.postMessage(response);
        })
    );
    // Windows Inspector - Create listeners for BE (Python) messages
    context.subscriptions.push(
        langServer.onNotification("$/windowsPick", (values) => {
            const pickedLocator: WindowsAppTree = JSON.stringify(values["picked"]) as unknown as WindowsAppTree;
            OUTPUT_CHANNEL.appendLine(`> Receiving: picked.element: ${pickedLocator}`);
            const response: IEventMessage = {
                id: "",
                type: IMessageType.EVENT,
                event: {
                    type: "pickedWinLocatorTree",
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
        sendRequest("windowsInspectorStopPick", {});
        sendRequest("windowsInspectorStopHighlight", {});
        ROBOCORP_INSPECTOR_IS_OPENED = false;
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
                        OUTPUT_CHANNEL.appendLine(`> Requesting: Get Locators: ${JSON.stringify(command)}`);
                        const actionResult: ActionResult<LocatorsMap> = await sendRequest("loadRobotLocatorContents", {
                            directory: directory,
                        });
                        OUTPUT_CHANNEL.appendLine(`> Requesting: Response: ${JSON.stringify(actionResult)}`);
                        panel.webview.postMessage(
                            buildProtocolResponseFromActionResponse(message, actionResult, "locatorsMap")
                        );
                    } else if (message.app === IApps.LOCATORS_MANAGER) {
                        if (command["type"] === "delete") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Delete Locators: ${command["ids"]}`);
                            const actionResult: ActionResult<any> = await sendRequest("managerDeleteLocators", {
                                directory: directory,
                                ids: command["ids"],
                            });
                            panel.webview.postMessage(buildProtocolResponseFromActionResponse(message, actionResult));
                        } else if (command["type"] === "save") {
                            const locator = message["command"]["locator"];
                            const actionResult: ActionResult<any> = await sendRequest("managerSaveLocator", {
                                locator: locator,
                                directory: directory,
                            });
                            panel.webview.postMessage(buildProtocolResponseFromActionResponse(message, actionResult));
                        }
                    } else if (message.app === IApps.WEB_INSPECTOR) {
                        if (command["type"] === "startPicking") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Start Picking: ${JSON.stringify(command)}`);
                            await sendRequest("webInspectorStartPick", { url_if_new: command["url"] });
                        } else if (command["type"] === "stopPicking") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Stop Picking: ${JSON.stringify(command)}`);
                            await sendRequest("webInspectorStopPick");
                        } else if (command["type"] === "validate") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Validate: ${JSON.stringify(command)}`);
                            const actionResult = await sendRequest("webInspectorValidateLocator", {
                                locator: command["locator"],
                                url: command["url"],
                            });
                            OUTPUT_CHANNEL.appendLine(`> Requesting: Result: ${JSON.stringify(actionResult)}`);
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locatorMatches")
                            );
                        }
                    } else if (message.app === IApps.WINDOWS_INSPECTOR) {
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
                        } else if (command["type"] === "startHighlighting") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: startHighlighting: ${JSON.stringify(command)}`);
                            const actionResult: ActionResult<any> = await sendRequest(
                                "windowsInspectorStartHighlight",
                                {
                                    locator: command["locator"],
                                    search_depth: command["depth"] || 8,
                                    search_strategy: command["strategy"] || "all",
                                }
                            );
                            OUTPUT_CHANNEL.appendLine(`> Requesting: result: ${JSON.stringify(actionResult)}`);
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locator")
                            );
                        } else if (command["type"] === "stopHighlighting") {
                            OUTPUT_CHANNEL.appendLine(`> Requesting: stopHighlighting: ${JSON.stringify(command)}`);
                            const actionResult: ActionResult<any> = await sendRequest("windowsInspectorStopHighlight");
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

function getWebviewContent(directory: string, jsonData: LocatorsMap, startRoute?: InspectorAppRoutes): string {
    // get the template that's created via the inspector-ext
    const templateFile = getExtensionRelativeFile("../../vscode-client/templates/inspector.html", true);
    const data = readFileSync(templateFile, "utf8");

    // inject the locators.json contents
    const startLocators = '<script id="locatorsJSON" type="application/json">';
    const startIndexLocators = data.indexOf(startLocators) + startLocators.length;
    const endLocators = "</script>";
    const endIndexLocators = data.indexOf(endLocators, startIndexLocators);

    const contentLocators = JSON.stringify(
        { location: directory, locatorsLocation: path.join(directory, "locators.json"), data: jsonData },
        null,
        4
    );
    const retLocators: string =
        data.substring(0, startIndexLocators) + contentLocators + data.substring(endIndexLocators);

    // inject the controls json
    const startControl = '<script id="controlJSON" type="application/json">';
    const startIndexControl = retLocators.indexOf(startControl) + startControl.length;
    const endControl = "</script>";
    const endIndexControl = retLocators.indexOf(endControl, startIndexControl);

    const controlContent = JSON.stringify({ startRoute: startRoute || InspectorAppRoutes.LOCATORS_MANAGER }, null, 4);
    const retControl: string =
        retLocators.substring(0, startIndexControl) + controlContent + retLocators.substring(endIndexControl);

    return retControl;
}
