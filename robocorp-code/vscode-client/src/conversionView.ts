/**
 * Interesting docs related to webviews:
 * https://code.visualstudio.com/api/extension-guides/webview
 */
import { readFileSync } from "fs";
import * as vscode from "vscode";
import { getExtensionRelativeFile } from "./files";

interface ConversionInfoLastOptions {
    input: string[];
    analysisResults: string;
    generationResults: string;
    outputFolder: string;
}

enum RPATypes {
    uipath = "uipath",
    blueprism = "blueprism",
    a360 = "a360",
}

const TYPE_TO_CAPTION = {
    "uipath": "UiPath",
    "blueprism": "Blue Prism",
    "a360": "Automation Anywhere 360",
};

interface ConversionInfo {
    inputType: RPATypes;
    input: string[];
    analysisResults: string;
    generationResults: string;
    outputFolder: string;
    typeToLastOptions: Map<RPATypes, ConversionInfoLastOptions>;
}

let panel: vscode.WebviewPanel | undefined = undefined;

export async function showConvertUI(
    context: vscode.ExtensionContext,
    convertBundlePromise: Promise<{
        pathToExecutable: string;
        pathToConvertYaml?: string;
    }>
) {
    if (!panel) {
        panel = vscode.window.createWebviewPanel("robocorpCodeConvert", "RPA Converter", vscode.ViewColumn.One, {
            enableScripts: true,
            retainContextWhenHidden: true,
        });
        panel.onDidDispose(() => {
            panel = undefined;
        });
    } else {
        panel.reveal();
        return;
    }

    const typeToLastOptions = new Map<RPATypes, ConversionInfoLastOptions>;
    typeToLastOptions[RPATypes.uipath] = {
        "input": [], // files or folders
        "analysisResults": "",
        "generationResults": "",
        "outputFolder": "",
    }
    typeToLastOptions[RPATypes.blueprism] = {
        "input": [], // files or folders
        "analysisResults": "",
        "generationResults": "",
        "outputFolder": "",
    }
    typeToLastOptions[RPATypes.a360] = {
        "input": [], // files or folders
        "analysisResults": "",
        "generationResults": "",
        "outputFolder": "",
    }

    const conversionInfo: ConversionInfo = {
        "inputType": RPATypes.uipath,
        "input": [],
        "analysisResults": "",
        "generationResults": "",
        "outputFolder": "",

        "typeToLastOptions": typeToLastOptions
    };

    const wsFolders: ReadonlyArray<vscode.WorkspaceFolder> = vscode.workspace.workspaceFolders;
    let ws: vscode.WorkspaceFolder;
    if (wsFolders !== undefined && wsFolders.length >= 1) {
        ws = wsFolders[0];
        conversionInfo.outputFolder = ws.uri.fsPath;
    }

    panel.webview.html = getWebviewContent(conversionInfo);
    panel.webview.onDidReceiveMessage(
        async (message) => {
            switch (message.command) {
                case "onClickAdd":
                    let input: string[] = [];
                    try {
                        const contents = message.contents;
                        const type: RPATypes = contents["type"];
                        const vendor = TYPE_TO_CAPTION[type];
                        if (!vendor) {
                            vscode.window.showErrorMessage("Error: unable to handle type: " + type);
                            return;
                        }
                        let uris: vscode.Uri[];
                        if (type === RPATypes.blueprism) {
                            // select files
                            uris = await vscode.window.showOpenDialog({
                                "canSelectFolders": false,
                                "canSelectFiles": true,
                                "canSelectMany": true,
                                "openLabel": `Select a ${vendor} file project to convert`,
                            });
                        } else {
                            // select folders
                            uris = await vscode.window.showOpenDialog({
                                "canSelectFolders": true,
                                "canSelectFiles": false,
                                "canSelectMany": true,
                                "openLabel": `Select a ${vendor} folder project to convert`,
                            });
                        }
                        if (uris && uris.length > 0) {
                            for (const uri of uris) {
                                input.push(uri.fsPath);
                            }
                        }
                    } finally {
                        panel.webview.postMessage({ command: "addFileOrFolder", "input": input });
                    }
                    return;
            }
        },
        undefined,
        context.subscriptions
    );
}

function getWebviewContent(jsonData: ConversionInfo): string {
    const jsonDataStr = JSON.stringify(jsonData, null, 4);
    const templateFile = getExtensionRelativeFile("../../vscode-client/templates/converter.html", true);
    const data = readFileSync(templateFile, "utf8");

    const start = '<script id="data" type="application/json">';
    const startI = data.indexOf(start) + start.length;
    const end = "</script>";
    const endI = data.indexOf(end, startI);

    const ret: string = data.substring(0, startI) + jsonDataStr + data.substring(endI);
    return ret;
}
