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
import { BrowserLocator, ImageLocator, LocatorsMap, LocatorType } from "./types";
import {
    ReportedStates,
    IApps,
    IEventMessage,
    IMessage,
    IMessageType,
    IRequestMessage,
    IResponseMessage,
    IAppRoutes,
    ResponseDataType,
    WindowsAppTree,
    ImagePickResponse,
    JavaAppTree,
} from "./protocols";
import { langServer } from "../extension";
import { ActionResult, LocalRobotMetadataInfo } from "../protocols";
import { ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL } from "../robocorpCommands";
import { generateID } from "./utils";

// singleton objects
let ROBOCORP_INSPECTOR_PANEL: vscode.WebviewPanel | undefined = undefined;

let ROBOT_DIRECTORY: string | undefined = undefined;

// showInspectorUI - registered function for opening the Inspector while calling VSCode commands
export async function showInspectorUI(context: vscode.ExtensionContext, route?: IAppRoutes) {
    if (ROBOCORP_INSPECTOR_PANEL !== undefined) {
        OUTPUT_CHANNEL.appendLine("# Robocorp Inspector is already opened! Thank you!");
        OUTPUT_CHANNEL.appendLine(`# Switching to the commanded Route: ${route}`);
        const response: IEventMessage = {
            id: "",
            type: IMessageType.EVENT,
            event: {
                type: "gotoInspectorApp",
                status: "success",
                data: route,
            },
        };
        // this is an event - postMessage will update the useLocator hook
        ROBOCORP_INSPECTOR_PANEL.webview.postMessage(response);
        ROBOCORP_INSPECTOR_PANEL.reveal();
        return;
    }
    OUTPUT_CHANNEL.appendLine(`# Robocorp Inspector is ROBOCORP_INSPECTOR_PANEL: ${ROBOCORP_INSPECTOR_PANEL}`);

    const panel = vscode.window.createWebviewPanel(
        "robocorpCodeInspector",
        "Robocorp Inspector",
        vscode.ViewColumn.Active,
        {
            enableScripts: true,
            retainContextWhenHidden: true,
        }
    );
    ROBOCORP_INSPECTOR_PANEL = panel;

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
        ROBOT_DIRECTORY = directory;
    }

    let locatorsMap = {};
    if (locatorJson) {
        if (verifyFileExists(locatorJson, false)) {
            let doc = await vscode.workspace.openTextDocument(vscode.Uri.file(locatorJson));
            locatorsMap = JSON.parse(doc.getText()) as LocatorsMap;
        }
    }
    const onDiskPath = vscode.Uri.file(directory);
    const directoryURI = panel.webview.asWebviewUri(onDiskPath);
    OUTPUT_CHANNEL.appendLine(`> ON DISK PATH ROBOT DIRECTORY: ${directoryURI.toString()}`);
    panel.webview.html = getWebviewContent(directory, directoryURI.toString(), locatorsMap, route);

    // Web Inspector - Create listeners for BE (Python) messages
    context.subscriptions.push(
        langServer.onNotification("$/webPick", (values) => {
            const pickedLocator: BrowserLocator = JSON.stringify(values) as unknown as BrowserLocator;
            OUTPUT_CHANNEL.appendLine(`[Web] > Receiving: picked.element: ${pickedLocator}`);
            const response: IEventMessage = {
                id: generateID(),
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
            OUTPUT_CHANNEL.appendLine(`[Web] > Receiving: webInspectorState: ${JSON.stringify(state)}`);
            const response: IEventMessage = {
                id: generateID(),
                type: IMessageType.EVENT,
                event: {
                    type: "browserState",
                    status: "success",
                    data: state.state as ReportedStates,
                },
            };
            // this is an event - postMessage will update the useLocator hook
            panel.webview.postMessage(response);
        })
    );
    context.subscriptions.push(
        langServer.onNotification("$/webURLChange", (url) => {
            OUTPUT_CHANNEL.appendLine(`[Web] > Receiving: webURLChange: ${JSON.stringify(url)}`);
            const response: IEventMessage = {
                id: generateID(),
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
    context.subscriptions.push(
        langServer.onNotification("$/webReigniteThread", async (values) => {
            OUTPUT_CHANNEL.appendLine(`[Web] > Receiving: webReigniteThread: ${JSON.stringify(values)}`);
            const browserConfig: {
                browser_config: { viewport_size: [number, number] };
                url?: string;
            } = values as {
                browser_config: { viewport_size: any };
                url?: string;
            };
            await sendRequest("webInspectorConfigureBrowser", {
                width: browserConfig.browser_config.viewport_size[0],
                height: browserConfig.browser_config.viewport_size[1],
                url: browserConfig.url !== "" ? browserConfig.url : undefined,
            });
            await sendRequest("webInspectorStartPick", {
                url_if_new: browserConfig.url !== "" ? browserConfig.url : undefined,
            });
        })
    );
    // Windows Inspector - Create listeners for BE (Python) messages
    context.subscriptions.push(
        langServer.onNotification("$/windowsPick", (values) => {
            const pickedLocator: WindowsAppTree = JSON.stringify(values["picked"]) as unknown as WindowsAppTree;
            OUTPUT_CHANNEL.appendLine(`[Windows] > Receiving: picked.element: ${pickedLocator}`);
            const response: IEventMessage = {
                id: generateID(),
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
    // Image Inspector - Create listeners for BE (Python) messages
    context.subscriptions.push(
        langServer.onNotification("$/imagePick", (values) => {
            const pickedLocator: ImagePickResponse = JSON.stringify(values["picked"]) as unknown as ImagePickResponse;
            OUTPUT_CHANNEL.appendLine(`[Image] > Receiving: picked.element: ${pickedLocator}`);
            const response: IEventMessage = {
                id: generateID(),
                type: IMessageType.EVENT,
                event: {
                    type: "pickedImageSnapshot",
                    status: "success",
                    data: pickedLocator,
                },
            };
            // this is an event - postMessage will update the useLocator hook
            panel.webview.postMessage(response);
        })
    );
    context.subscriptions.push(
        langServer.onNotification("$/imageValidation", (values) => {
            const matches: number = JSON.stringify(values["matches"]) as unknown as number;
            OUTPUT_CHANNEL.appendLine(`[Image] > Receiving: matches: ${matches}`);
            const response: IEventMessage = {
                id: generateID(),
                type: IMessageType.EVENT,
                event: {
                    type: "pickedImageValidation",
                    status: "success",
                    data: matches,
                },
            };
            // this is an event - postMessage will update the useLocator hook
            panel.webview.postMessage(response);
        })
    );
    context.subscriptions.push(
        langServer.onNotification("$/imageInspectorState", (state) => {
            OUTPUT_CHANNEL.appendLine(`[Image] > Receiving: imageInspectorState: ${JSON.stringify(state)}`);
            const response: IEventMessage = {
                id: generateID(),
                type: IMessageType.EVENT,
                event: {
                    type: "snippingToolState",
                    status: "success",
                    data: state.state as ReportedStates,
                },
            };
            // this is an event - postMessage will update the useLocator hook
            panel.webview.postMessage(response);
        })
    );
    // Java Inspector - Create listeners for BE (Python) messages
    context.subscriptions.push(
        langServer.onNotification("$/javaPick", (values) => {
            const pickedLocator: JavaAppTree = JSON.stringify(values["picked"]) as unknown as JavaAppTree;
            OUTPUT_CHANNEL.appendLine(`[Java] > Receiving: picked.element: ${pickedLocator}`);
            const response: IEventMessage = {
                id: generateID(),
                type: IMessageType.EVENT,
                event: {
                    type: "pickedJavaLocatorTree",
                    status: "success",
                    data: pickedLocator,
                },
            };
            // this is an event - postMessage will update the useLocator hook
            panel.webview.postMessage(response);
        })
    );

    panel.onDidDispose(() => {
        OUTPUT_CHANNEL.appendLine(`> Killing all Inspectors...`);
        sendRequest("killInspectors", { inspector: null });
        ROBOCORP_INSPECTOR_PANEL = undefined;
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
                        const actionResult: ActionResult<LocatorsMap> = await sendRequest("managerLoadLocators", {
                            directory: directory,
                        });
                        OUTPUT_CHANNEL.appendLine(`[Manager] > Requesting: Response: ${JSON.stringify(actionResult)}`);
                        panel.webview.postMessage(
                            buildProtocolResponseFromActionResponse(message, actionResult, "locatorsMap")
                        );
                    } else if (message.app === IApps.LOCATORS_MANAGER) {
                        if (command["type"] === "delete") {
                            OUTPUT_CHANNEL.appendLine(`[Manager] > Requesting: Delete Locators: ${command["ids"]}`);
                            const actionResult: ActionResult<any> = await sendRequest("managerDeleteLocators", {
                                directory: directory,
                                ids: command["ids"],
                            });
                            panel.webview.postMessage(buildProtocolResponseFromActionResponse(message, actionResult));
                        } else if (command["type"] === "save") {
                            const locator = message["command"]["locator"];
                            OUTPUT_CHANNEL.appendLine(
                                `[Manager] > Requesting: Save Locator: ${JSON.stringify(locator)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("managerSaveLocator", {
                                locator: locator,
                                directory: directory,
                            });
                            panel.webview.postMessage(buildProtocolResponseFromActionResponse(message, actionResult));
                        }
                    } else if (message.app === IApps.WEB_INSPECTOR) {
                        if (command["type"] === "startPicking") {
                            // configure the browser before opening anything
                            OUTPUT_CHANNEL.appendLine(
                                `[Web] > Requesting: Configure Browser: ${JSON.stringify(command)}`
                            );
                            await sendRequest("webInspectorConfigureBrowser", {
                                width: command["viewportWidth"],
                                height: command["viewportHeight"],
                                url: command["url"],
                            });
                            // start picking
                            OUTPUT_CHANNEL.appendLine(`[Web] > Requesting: Start Picking: ${JSON.stringify(command)}`);
                            await sendRequest("webInspectorStartPick", {
                                url_if_new: command["url"],
                            });
                        } else if (command["type"] === "stopPicking") {
                            OUTPUT_CHANNEL.appendLine(`[Web] > Requesting: Stop Picking: ${JSON.stringify(command)}`);
                            await sendRequest("webInspectorStopPick");
                        } else if (command["type"] === "validate") {
                            OUTPUT_CHANNEL.appendLine(`[Web] > Requesting: Validate: ${JSON.stringify(command)}`);
                            const actionResult = await sendRequest("webInspectorValidateLocator", {
                                locator: command["locator"],
                                url: command["url"],
                            });
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locatorMatches")
                            );
                        } else if (command["type"] === "killMe") {
                            await sendRequest("killInspectors", { inspector: LocatorType.Browser });
                        }
                    } else if (message.app === IApps.WINDOWS_INSPECTOR) {
                        if (command["type"] === "startPicking") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Windows] > Requesting: Start Picking: ${JSON.stringify(command)}`
                            );
                            await sendRequest("windowsInspectorStartPick");
                        } else if (command["type"] === "stopPicking") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Windows] > Requesting: Stop Picking: ${JSON.stringify(command)}`
                            );
                            await sendRequest("windowsInspectorStopPick");
                        } else if (command["type"] === "getAppWindows") {
                            OUTPUT_CHANNEL.appendLine(`[Windows] > Requesting: Get Apps: ${JSON.stringify(command)}`);
                            const actionResult: ActionResult<any> = await sendRequest("windowsInspectorListWindows");
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "winApps")
                            );
                        } else if (command["type"] === "setSelectedApp") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Windows] > Requesting: Set Selected App: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest(
                                "windowsInspectorSetWindowLocator",
                                { locator: `handle:${command["handle"]}` }
                            );
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result)
                            );
                        } else if (command["type"] === "collectAppTree") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Windows] > Requesting: Collect App Tree: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("windowsInspectorCollectTree", {
                                locator: command["locator"],
                                search_depth: command["depth"] || 8,
                                search_strategy: command["strategy"] || "all",
                            });
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "winAppTree")
                            );
                        } else if (command["type"] === "validateLocatorSyntax") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Windows] > Requesting: Validate Locator Syntax: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("windowsInspectorParseLocator", {
                                locator: command["locator"],
                            });
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locator")
                            );
                        } else if (command["type"] === "startHighlighting") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Windows] > Requesting: Start Highlighting: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest(
                                "windowsInspectorStartHighlight",
                                {
                                    locator: command["locator"],
                                    search_depth: command["depth"] || 8,
                                    search_strategy: command["strategy"] || "all",
                                }
                            );
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locator")
                            );
                        } else if (command["type"] === "stopHighlighting") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Windows] > Requesting: Stop Highlighting: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("windowsInspectorStopHighlight");
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locator")
                            );
                        } else if (command["type"] === "killMe") {
                            await sendRequest("killInspectors", { inspector: LocatorType.Windows });
                        }
                    } else if (message.app === IApps.IMAGE_INSPECTOR) {
                        if (command["type"] === "startPicking") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Image] > Requesting: Start Picking: ${JSON.stringify(command)}`
                            );
                            await sendRequest("imageInspectorStartPick", {
                                minimize: command["minimize"],
                                confidence_level: command["confidenceLevel"],
                            });
                        } else if (command["type"] === "stopPicking") {
                            OUTPUT_CHANNEL.appendLine(`[Image] > Requesting: Stop Picking: ${JSON.stringify(command)}`);
                            await sendRequest("imageInspectorStopPick");
                        } else if (command["type"] === "validate") {
                            OUTPUT_CHANNEL.appendLine(`[Image] > Requesting: Validate: ${JSON.stringify(command)}`);
                            await sendRequest("imageInspectorValidateLocator", {
                                locator: command["locator"],
                                confidence_level: (command["locator"] as ImageLocator).confidence,
                            });
                        } else if (command["type"] === "saveImage") {
                            OUTPUT_CHANNEL.appendLine(`[Image] > Requesting: SaveImage: ${JSON.stringify(command)}`);
                            const actionResult = await sendRequest("imageInspectorSaveImage", {
                                root_directory: ROBOT_DIRECTORY,
                                image_base64: command["imageBase64"],
                            });
                            OUTPUT_CHANNEL.appendLine(`[Image] > Result: SaveImage: ${JSON.stringify(actionResult)}`);
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "imagePath")
                            );
                        } else if (command["type"] === "killMe") {
                            await sendRequest("killInspectors", { inspector: LocatorType.Image });
                        }
                    } else if (message.app === IApps.JAVA_INSPECTOR) {
                        if (command["type"] === "startPicking") {
                            OUTPUT_CHANNEL.appendLine(`[Java] > Requesting: Start Picking: ${JSON.stringify(command)}`);
                            await sendRequest("javaInspectorStartPick");
                        } else if (command["type"] === "stopPicking") {
                            OUTPUT_CHANNEL.appendLine(`[Java] > Requesting: Stop Picking: ${JSON.stringify(command)}`);
                            await sendRequest("javaInspectorStopPick");
                        } else if (command["type"] === "getAppJava") {
                            OUTPUT_CHANNEL.appendLine(`[Java] > Requesting: Get Apps: ${JSON.stringify(command)}`);
                            const actionResult: ActionResult<any> = await sendRequest("javaInspectorListWindows");
                            OUTPUT_CHANNEL.appendLine(`[Java] > Result: Get Apps: ${JSON.stringify(actionResult)}`);
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "javaApps")
                            );
                        } else if (command["type"] === "setSelectedApp") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Requesting: Set Selected App: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("javaInspectorSetWindowLocator", {
                                locator: `${command["handle"]}`,
                            });
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Result: Set Selected Apps: ${JSON.stringify(actionResult)}`
                            );
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result)
                            );
                        } else if (command["type"] === "collectAppTree") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Requesting: Collect App Tree: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("javaInspectorCollectTree", {
                                locator: command["locator"],
                                search_depth: command["depth"] || 8,
                            });
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Result: Collect App Apps: ${JSON.stringify(actionResult)}`
                            );
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "javaAppTree")
                            );
                        } else if (command["type"] === "validateLocatorSyntax") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Requesting: Validate Locator Syntax: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("javaInspectorParseLocator", {
                                locator: command["locator"],
                            });
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Result: Validate Locator Apps: ${JSON.stringify(actionResult)}`
                            );
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locator")
                            );
                        } else if (command["type"] === "startHighlighting") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Requesting: Start Highlighting: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("javaInspectorStartHighlight", {
                                locator: command["locator"],
                                search_depth: command["depth"] || 8,
                            });
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Result: Start Highlighting: ${JSON.stringify(actionResult)}`
                            );
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locator")
                            );
                        } else if (command["type"] === "stopHighlighting") {
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Requesting: Stop Highlighting: ${JSON.stringify(command)}`
                            );
                            const actionResult: ActionResult<any> = await sendRequest("javaInspectorStopHighlight");
                            OUTPUT_CHANNEL.appendLine(
                                `[Java] > Result: Stop Highlighting: ${JSON.stringify(actionResult)}`
                            );
                            panel.webview.postMessage(
                                buildProtocolResponseFromActionResponse(message, actionResult.result, "locator")
                            );
                        } else if (command["type"] === "killMe") {
                            await sendRequest("killInspectors", { inspector: LocatorType.Java });
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

function getWebviewContent(
    directory: string,
    directoryURI: string,
    jsonData: LocatorsMap,
    startRoute?: IAppRoutes
): string {
    // get the template that's created via the inspector-ext
    const templateFile = getExtensionRelativeFile("../../vscode-client/templates/inspector.html", true);
    const data = readFileSync(templateFile, "utf8");

    // inject the locators.json contents
    const startLocators = '<script id="locatorsJSON" type="application/json">';
    const startIndexLocators = data.indexOf(startLocators) + startLocators.length;
    const endLocators = "</script>";
    const endIndexLocators = data.indexOf(endLocators, startIndexLocators);

    const contentLocators = JSON.stringify(
        {
            location: directory,
            locationURI: directoryURI,
            locatorsLocation: path.join(directory, "locators.json"),
            data: jsonData,
        },
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

    const controlContent = JSON.stringify({ startRoute: startRoute || IAppRoutes.LOCATORS_MANAGER }, null, 4);
    const retControl: string =
        retLocators.substring(0, startIndexControl) + controlContent + retLocators.substring(endIndexControl);

    return retControl;
}
