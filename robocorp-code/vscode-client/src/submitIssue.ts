/**
 * Interesting docs related to webviews:
 * https://code.visualstudio.com/api/extension-guides/webview
 */
import { readFileSync } from "fs";
import * as vscode from "vscode";
import { logError } from "./channel";
import { getExtensionRelativeFile } from "./files";
import { ActionResult, IAccountInfo } from "./protocols";
import { CollectedLogs, collectIssueLogs, submitIssue } from "./rcc";
import { ROBOCORP_GET_LINKED_ACCOUNT_INFO_INTERNAL } from "./robocorpCommands";

export async function showSubmitIssueUI(context: vscode.ExtensionContext) {
    const info = await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: "Collecting information to submit issue...",
            cancellable: false,
        },
        async () => {
            const collectedLogs: CollectedLogs = await collectIssueLogs(context.logUri.fsPath);
            let email = "";
            try {
                let accountInfoResult: ActionResult<IAccountInfo> = await vscode.commands.executeCommand(
                    ROBOCORP_GET_LINKED_ACCOUNT_INFO_INTERNAL
                );

                if (accountInfoResult.success) {
                    email = accountInfoResult.result.email;
                }
            } catch (err) {
                logError("Error getting default e-mail.", err, "SEND_ISSUE_ERROR_GETTING_DEFAULT_EMAIL");
            }
            return { collectedLogs, email };
        }
    );

    const collectedLogs = info.collectedLogs;
    const email = info.email;

    const panel = vscode.window.createWebviewPanel(
        "robocorpCodeSubmitIssue",
        "Submit Issue to Robocorp",
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true,
        }
    );

    panel.webview.html = getWebviewContent({ "files": collectedLogs.logFiles, "email": email });
    panel.webview.onDidReceiveMessage(
        async (message) => {
            switch (message.command) {
                case "onClickViewFile":
                    const file = message.filename;
                    vscode.commands.executeCommand("vscode.open", vscode.Uri.file(file));
                    return;
                case "onClickSubmit":
                    const contents: IReportContents = message.contents;
                    try {
                        await submitIssue(
                            contents.details,
                            contents.email,
                            "Robocorp Code",
                            "Robocorp Code",
                            contents.summary,
                            contents.files
                        );
                    } finally {
                        panel.webview.postMessage({ command: "issueSent" });
                    }
                    return;
            }
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

interface ISubmitIssueInput {
    files: string[];
    email: string;
}

function getWebviewContent(jsonData: ISubmitIssueInput): string {
    const jsonDataStr = JSON.stringify(jsonData, null, 4);
    const templateFile = getExtensionRelativeFile("../../vscode-client/templates/submit_issue.html", true);
    const data = readFileSync(templateFile, "utf8");

    const start = '<script id="data" type="application/json">';
    const startI = data.indexOf(start) + start.length;
    const end = "</script>";
    const endI = data.indexOf(end, startI);

    const ret: string = data.substring(0, startI) + jsonDataStr + data.substring(endI);
    return ret;
}
