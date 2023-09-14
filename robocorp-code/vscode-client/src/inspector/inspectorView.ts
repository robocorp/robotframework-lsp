/**
 * Interesting docs related to webviews:
 * https://code.visualstudio.com/api/extension-guides/webview
 */
import path = require("path");
import { readFileSync } from "fs";

import * as vscode from "vscode";

import { getExtensionRelativeFile, verifyFileExists } from "../files";
import { logError } from "../channel";
import { getSelectedRobot } from "../viewsCommon";
import { LocatorsMap } from "./types";
import { IMessage, IMessageType } from "./protocols";

export async function showInspectorUI(context: vscode.ExtensionContext) {
    const panel = vscode.window.createWebviewPanel(
        "robocorpCodeInspector",
        "Robocorp Inspector",
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true,
        }
    );

    const robot = getSelectedRobot();
    if (robot) {
        let locatorJson = path.join(robot.robot.directory, "locators.json");
        if (verifyFileExists(locatorJson, false)) {
            vscode.workspace.openTextDocument(vscode.Uri.file(locatorJson)).then((document) => {
                let text = document.getText();
                panel.webview.html = getWebviewContent(JSON.parse(text) as LocatorsMap);
            });
        } else {
            logError("locators.json.not.found", undefined, "");
        }
    } else {
        logError("robot.not.found", undefined, "");
    }

    panel.webview.onDidReceiveMessage(
        async (message: IMessage) => {
            logError(`incoming.message: ${JSON.stringify(message)}`, undefined, "");
            switch (message.type) {
                case IMessageType.REQUEST:
                    logError(`incoming.request: ${JSON.stringify(message)}`, undefined, "");
                    return;
                case IMessageType.RESPONSE:
                    logError(`incoming.response: ${JSON.stringify(message)}`, undefined, "");
                    return;
                case IMessageType.EVENT:
                    logError(`incoming.event: ${JSON.stringify(message)}`, undefined, "");
                    return;
                default:
                    logError(`unhandled.message: ${JSON.stringify(message)}`, undefined, "");
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
