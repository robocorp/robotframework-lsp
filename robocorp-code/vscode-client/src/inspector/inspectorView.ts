/**
 * Interesting docs related to webviews:
 * https://code.visualstudio.com/api/extension-guides/webview
 */
import { readFileSync } from "fs";
import * as vscode from "vscode";
import { getExtensionRelativeFile, verifyFileExists } from "../files";
import { logError } from "../channel";
import { getSelectedRobot } from "../viewsCommon";
import path = require("path");

export async function showInspectorUI(context: vscode.ExtensionContext) {
    const panel = vscode.window.createWebviewPanel(
        "robocorpCodeInspector",
        "Open Robocorp Inspector",
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
                panel.webview.html = getWebviewContent(JSON.parse(text) as ILocatorsJSON);
            });
        } else {
            logError("locators.json.not.found", undefined, "");
        }
    } else {
        logError("robot.not.found", undefined, "");
    }

    panel.webview.onDidReceiveMessage(
        async (message) => {
            logError(`incoming.contents: ${JSON.stringify(message)}`, undefined, "");
            // switch (message.command) {
            //     case "onClickViewFile":
            //         const file = message.filename;
            //         vscode.commands.executeCommand("vscode.open", vscode.Uri.file(file));
            //         return;
            //     case "onClickSubmit":
            //         const contents: IReportContents = message.contents;
            //         try {
            //             logError(
            //                 `incoming.contents: ${contents}`,
            //                 new Error(),
            //                 "SEND_ISSUE_ERROR_GETTING_DEFAULT_EMAIL"
            //             );
            //         } finally {
            //             panel.webview.postMessage({ command: "issueSent" });
            //         }
            //         return;
            // }
        },
        undefined,
        context.subscriptions
    );
}

interface IReportContents {
    email: string;
    summary: string;
    details: string;
    files: string[];
}

interface ILocatorsJSON {
    [key: string]: object;
}

function getWebviewContent(jsonData: ILocatorsJSON): string {
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
