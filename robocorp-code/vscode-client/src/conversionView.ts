/**
 * Interesting docs related to webviews:
 * https://code.visualstudio.com/api/extension-guides/webview
 */
import { readFileSync } from "fs";
import { dirname } from "path";
import * as vscode from "vscode";
import { logError } from "./channel";
import {
    ensureConvertBundle,
    convertAndSaveResults,
    RPATypes,
    RPA_TYPE_TO_CAPTION,
    getConverterVersion,
} from "./conversion";
import { getExtensionRelativeFile } from "./files";

interface ConversionInfoLastOptions {
    input: string[];
    generationResults: string;
    outputFolder: string;
    apiFolder: string;
}

interface ConversionInfo {
    inputType: RPATypes;
    input: string[];
    generationResults: string;
    outputFolder: string;
    apiFolder: string;
    typeToLastOptions: Map<RPATypes, ConversionInfoLastOptions>;
    latestVersion: string;
}

let panel: vscode.WebviewPanel | undefined = undefined;
let globalState: vscode.Memento = undefined;

export async function showConvertUI(context: vscode.ExtensionContext) {
    const convertBundlePromise: Promise<{
        pathToExecutable: string;
        pathToConvertYaml?: string;
    }> = ensureConvertBundle();
    const converterVersion = await getConverterVersion();

    globalState = context.globalState;

    if (!panel) {
        panel = vscode.window.createWebviewPanel(
            "robocorpCodeConvert",
            `Conversion Accelerator v${converterVersion}`,
            vscode.ViewColumn.One,
            {
                enableScripts: true,
            }
        );
        panel.onDidDispose(() => {
            panel = undefined;
        });
    } else {
        panel.reveal();
        return;
    }

    const wsFolders: ReadonlyArray<vscode.WorkspaceFolder> = vscode.workspace.workspaceFolders;
    let ws: vscode.WorkspaceFolder;
    let outputFolder = "";
    let apiFolder = "";
    if (wsFolders !== undefined && wsFolders.length >= 1) {
        ws = wsFolders[0];
        outputFolder = ws.uri.fsPath;
    }

    const typeToLastOptions = new Map<RPATypes, ConversionInfoLastOptions>();

    function generateDefaultOptions(): ConversionInfoLastOptions {
        return {
            "input": [], // files for BP, folders for others.
            "generationResults": "",
            "outputFolder": outputFolder,
            "apiFolder": apiFolder,
        };
    }

    typeToLastOptions[RPATypes.uipath] = generateDefaultOptions();
    typeToLastOptions[RPATypes.blueprism] = generateDefaultOptions();
    typeToLastOptions[RPATypes.a360] = generateDefaultOptions();
    typeToLastOptions[RPATypes.aav11] = generateDefaultOptions();

    let conversionInfo: ConversionInfo = {
        "inputType": RPATypes.uipath,
        "input": [],
        "generationResults": "",
        "outputFolder": outputFolder,
        "apiFolder": apiFolder,
        "latestVersion": converterVersion,
        "typeToLastOptions": typeToLastOptions,
    };

    const oldState = context.globalState.get("robocorpConversionViewState");
    if (oldState) {
        conversionInfo = <ConversionInfo>oldState;

        // Validate that what we had saved is valid for new versions.
        // i.e.: Backward-compatibility.
        if (conversionInfo.apiFolder === undefined) {
            conversionInfo.apiFolder = "";
        }

        // backward compatibility
        if (conversionInfo.latestVersion === undefined) {
            conversionInfo.latestVersion = converterVersion;
        }

        if (conversionInfo.typeToLastOptions[RPATypes.aav11] === undefined) {
            conversionInfo.typeToLastOptions[RPATypes.aav11] = generateDefaultOptions();
        }

        for (const [key, val] of Object.entries(conversionInfo.typeToLastOptions)) {
            if (val.apiFolder === undefined) {
                val.apiFolder = "";
            }
        }
    }

    panel.webview.html = getWebviewContent(conversionInfo);
    panel.webview.onDidReceiveMessage(
        async (message) => {
            switch (message.command) {
                case "persistState":
                    const stateToPersist = message.contents;
                    context.globalState.update("robocorpConversionViewState", stateToPersist);
                    return;
                case "onClickOutputFolder":
                    let outputFolder: string = "";
                    try {
                        const currentOutputFolder = message.currentOutputFolder;
                        outputFolder = await onClickOutputFolder(currentOutputFolder);
                    } finally {
                        panel.webview.postMessage({ command: "setOutputFolder", "outputFolder": outputFolder });
                    }
                    return;
                case "onClickApiFolder":
                    let apiFolder: string = "";
                    try {
                        const currentApiFolder = message.currentApiFolder;
                        apiFolder = await onClickApiFolder(currentApiFolder);
                    } finally {
                        panel.webview.postMessage({ command: "setApiFolder", "apiFolder": apiFolder });
                    }
                    return;
                case "onClickAdd":
                    let input: string[] = [];
                    try {
                        input = await onClickAdd(message.contents);
                    } finally {
                        panel.webview.postMessage({ command: "addFileOrFolder", "input": input });
                    }
                    return;
                case "onClickConvert":
                    let result: {
                        success: boolean;
                        message: string;
                    } = { success: false, message: "Unexpected error doing conversion." };
                    try {
                        const contents = message.contents;
                        const outputFolder = contents["outputFolder"];
                        const inputType = contents["inputType"];
                        const input = contents["input"];
                        const apiFolder = contents["apiFolder"];

                        result = await onClickConvert(convertBundlePromise, {
                            outputFolder,
                            inputType,
                            input,
                            apiFolder,
                        });
                    } finally {
                        panel.webview.postMessage({ command: "conversionFinished", result: result });
                    }
                    return;
            }
        },
        undefined,
        context.subscriptions
    );
}

async function onClickOutputFolder(currentOutputFolder: any): Promise<string> {
    const defaultUri = vscode.Uri.file(currentOutputFolder);
    let uris: vscode.Uri[] = await vscode.window.showOpenDialog({
        "canSelectFolders": true,
        "canSelectFiles": false,
        "canSelectMany": false,
        "openLabel": `Select output folder`,
        "defaultUri": defaultUri,
    });
    if (uris && uris.length > 0) {
        return uris[0].fsPath;
    }
    return "";
}

async function onClickApiFolder(currentApiFolder: any): Promise<string> {
    const defaultUri = vscode.Uri.file(currentApiFolder);
    let uris: vscode.Uri[] = await vscode.window.showOpenDialog({
        "canSelectFolders": true,
        "canSelectFiles": false,
        "canSelectMany": false,
        "openLabel": `Select API folder`,
        "defaultUri": defaultUri,
    });
    if (uris && uris.length > 0) {
        return uris[0].fsPath;
    }
    return "";
}

async function onClickAdd(contents: { type: RPATypes }): Promise<string[]> {
    const MEMENTO_KEY = `lastFolderFor${contents.type}`;
    const stored: string | undefined = globalState.get(MEMENTO_KEY);
    const lastFolder: vscode.Uri | undefined = stored ? vscode.Uri.file(stored) : undefined;

    let uris: vscode.Uri[];
    let input: string[] = [];
    const type: RPATypes = contents["type"];
    const vendor = RPA_TYPE_TO_CAPTION[type];
    if (!vendor) {
        vscode.window.showErrorMessage("Error: unable to handle type: " + type);
        return input;
    }

    if (type === RPATypes.blueprism || type === RPATypes.aav11) {
        // select files
        uris = await vscode.window.showOpenDialog({
            "canSelectFolders": false,
            "canSelectFiles": true,
            "canSelectMany": true,
            "openLabel": `Select a ${vendor} file project to convert`,
            "defaultUri": lastFolder,
        });
        if (uris && uris.length > 0) {
            globalState.update(MEMENTO_KEY, dirname(uris[0].fsPath));
            for (const uri of uris) {
                input.push(uri.fsPath);
            }
        }
    } else {
        // select folders
        uris = await vscode.window.showOpenDialog({
            "canSelectFolders": true,
            "canSelectFiles": false,
            "canSelectMany": true,
            "openLabel": `Select a ${vendor} folder project to convert`,
            "defaultUri": lastFolder,
        });
        if (uris && uris.length > 0) {
            globalState.update(MEMENTO_KEY, uris[0].fsPath);
            for (const uri of uris) {
                input.push(uri.fsPath);
            }
        }
    }
    return input;
}

async function onClickConvert(
    convertBundlePromise: Promise<{
        pathToExecutable: string;
        pathToConvertYaml?: string;
    }>,
    opts: {
        inputType: RPATypes;
        input: string[];
        outputFolder: string;
        apiFolder: string;
    }
): Promise<{
    success: boolean;
    message: string;
}> {
    try {
        return await convertAndSaveResults(convertBundlePromise, opts);
    } catch (error) {
        logError("Error making conversion.", error, "ERROR_CONVERTING_INTERNAL");
        return {
            "success": false,
            "message": "Error making conversion: " + error.message,
        };
    }
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
