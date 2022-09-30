/*
Original work Copyright (c) Microsoft Corporation (MIT)
See ThirdPartyNotices.txt in the project root for license information.
All modifications Copyright (c) Robocorp Technologies Inc.
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License")
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http: // www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

"use strict";

import * as net from "net";
import * as path from "path";
import * as vscode from "vscode";
import * as cp from "child_process";

import {
    workspace,
    Disposable,
    ExtensionContext,
    window,
    commands,
    extensions,
    env,
    Uri,
    WorkspaceFolder,
} from "vscode";
import { LanguageClientOptions, State } from "vscode-languageclient";
import { LanguageClient, ServerOptions } from "vscode-languageclient/node";
import * as inspector from "./inspector";
import { copySelectedToClipboard, removeLocator } from "./locators";
import * as views from "./views";
import * as roboConfig from "./robocorpSettings";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { fileExists, getExtensionRelativeFile, uriExists } from "./files";
import {
    feedbackAnyError,
    feedbackRobocorpCodeError,
    getEndpointUrl,
    getRccLocation,
    getRobocorpHome,
    submitIssue,
} from "./rcc";
import { Timing } from "./time";
import {
    createRobot,
    uploadRobot,
    cloudLogin,
    cloudLogout,
    setPythonInterpreterFromRobotYaml,
    askAndRunRobotRCC,
    rccConfigurationDiagnostics,
    updateLaunchEnvironment,
} from "./activities";
import { handleProgressMessage, ProgressReport } from "./progress";
import { TREE_VIEW_ROBOCORP_ROBOTS_TREE, TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE } from "./robocorpViews";
import { askAndCreateRccTerminal } from "./rccTerminal";
import {
    deleteResourceInRobotContentTree,
    newFileInRobotContentTree,
    newFolderInRobotContentTree,
    renameResourceInRobotContentTree,
} from "./viewsRobotContent";
import {
    convertOutputWorkItemToInput,
    deleteWorkItemInWorkItemsTree,
    newWorkItemInWorkItemsTree,
    openWorkItemHelp,
} from "./viewsWorkItems";
import { FSEntry, LocatorEntry, refreshTreeView, RobotEntry } from "./viewsCommon";
import {
    ROBOCORP_CLOUD_LOGIN,
    ROBOCORP_CLOUD_LOGOUT,
    ROBOCORP_CLOUD_UPLOAD_ROBOT_TREE_SELECTION,
    ROBOCORP_CONFIGURATION_DIAGNOSTICS,
    ROBOCORP_CONVERT_OUTPUT_WORK_ITEM_TO_INPUT,
    ROBOCORP_COPY_LOCATOR_TO_CLIPBOARD_INTERNAL,
    ROBOCORP_CREATE_RCC_TERMINAL_TREE_SELECTION,
    ROBOCORP_CREATE_ROBOT,
    ROBOCORP_DEBUG_ROBOT_RCC,
    ROBOCORP_DELETE_RESOURCE_IN_ROBOT_CONTENT_VIEW,
    ROBOCORP_DELETE_WORK_ITEM_IN_WORK_ITEMS_VIEW,
    ROBOCORP_EDIT_ROBOCORP_INSPECTOR_LOCATOR,
    ROBOCORP_GET_LANGUAGE_SERVER_PYTHON,
    ROBOCORP_GET_LANGUAGE_SERVER_PYTHON_INFO,
    ROBOCORP_HELP_WORK_ITEMS,
    ROBOCORP_NEW_FILE_IN_ROBOT_CONTENT_VIEW,
    ROBOCORP_NEW_FOLDER_IN_ROBOT_CONTENT_VIEW,
    ROBOCORP_NEW_ROBOCORP_INSPECTOR_BROWSER,
    ROBOCORP_NEW_ROBOCORP_INSPECTOR_IMAGE,
    ROBOCORP_NEW_WORK_ITEM_IN_WORK_ITEMS_VIEW,
    ROBOCORP_OPEN_CLOUD_HOME,
    ROBOCORP_OPEN_ROBOT_TREE_SELECTION,
    ROBOCORP_RCC_TERMINAL_NEW,
    ROBOCORP_REFRESH_CLOUD_VIEW,
    ROBOCORP_REFRESH_ROBOTS_VIEW,
    ROBOCORP_REFRESH_ROBOT_CONTENT_VIEW,
    ROBOCORP_REMOVE_LOCATOR_FROM_JSON,
    ROBOCORP_RENAME_RESOURCE_IN_ROBOT_CONTENT_VIEW,
    ROBOCORP_ROBOTS_VIEW_TASK_DEBUG,
    ROBOCORP_ROBOTS_VIEW_TASK_RUN,
    ROBOCORP_RUN_ROBOT_RCC,
    ROBOCORP_SET_PYTHON_INTERPRETER,
    ROBOCORP_SUBMIT_ISSUE,
    ROBOCORP_SUBMIT_ISSUE_INTERNAL,
    ROBOCORP_UPDATE_LAUNCH_ENV,
    ROBOCORP_UPLOAD_ROBOT_TO_CLOUD,
    ROBOCORP_ERROR_FEEDBACK_INTERNAL,
    ROBOCORP_OPEN_EXTERNALLY,
    ROBOCORP_OPEN_IN_VS_CODE,
    ROBOCORP_REVEAL_IN_EXPLORER,
    ROBOCORP_REVEAL_ROBOT_IN_EXPLORER,
    ROBOCORP_CONNECT_VAULT,
    ROBOCORP_DISCONNECT_VAULT,
    ROBOCORP_OPEN_VAULT_HELP,
    ROBOCORP_CLEAR_ENV_AND_RESTART,
    ROBOCORP_NEW_ROBOCORP_INSPECTOR_WINDOWS,
    ROBOCORP_SHOW_OUTPUT,
    ROBOCORP_SHOW_INTERPRETER_ENV_ERROR,
    ROBOCORP_FEEDBACK_INTERNAL,
    ROBOCORP_OPEN_FLOW_EXPLORER_TREE_SELECTION,
    ROBOCORP_OPEN_LOCATORS_JSON,
    ROBOCORP_OPEN_ROBOT_CONDA_TREE_SELECTION,
    ROBOCORP_CONVERT_PROJECT,
} from "./robocorpCommands";
import { installPythonInterpreterCheck } from "./pythonExtIntegration";
import { refreshCloudTreeView } from "./viewsRobocorp";
import { connectVault, disconnectVault } from "./vault";
import { getLanguageServerPythonInfoUncached } from "./extensionCreateEnv";
import { registerDebugger } from "./debugger";
import { clearRCCEnvironments, clearRobocorpCodeCaches, computeEnvsToCollect } from "./clear";
import { Mutex } from "./mutex";
import { mergeEnviron } from "./subprocess";
import { feedback } from "./rcc";
import { showSubmitIssueUI } from "./submitIssue";
import { ensureConvertBundle } from "./conversion";
import { TextDecoder } from "util";

interface InterpreterInfo {
    pythonExe: string;
    environ?: { [key: string]: string };
    additionalPythonpathEntries: string[];
}

const clientOptions: LanguageClientOptions = {
    documentSelector: [
        { language: "json", pattern: "**/locators.json" },
        { language: "yaml", pattern: "**/conda.yaml" },
        { language: "yaml", pattern: "**/robot.yaml" },
    ],
    synchronize: {
        configurationSection: "robocorp",
    },
    outputChannel: OUTPUT_CHANNEL,
};

const serverOptions: ServerOptions = async function () {
    let executableAndEnv: InterpreterInfo | undefined;
    function onNoPython() {
        OUTPUT_CHANNEL.appendLine(
            "Unable to activate Robocorp Code extension because python executable from RCC environment was not provided.\n" +
                " -- Most common reason is that the environment couldn't be created due to network connectivity issues.\n" +
                " -- Please fix the error and restart VSCode."
        );
        C.useErrorStubs = true;
        notifyOfInitializationErrorShowOutputTab();
    }

    try {
        // Note: we need to get it even in the case where we connect through a socket
        // as the debugger needs it afterwards to do other launches.
        executableAndEnv = await getLanguageServerPythonInfo();
        if (!executableAndEnv) {
            throw new Error("Unable to get language server python info.");
        }
    } catch (error) {
        onNoPython();
        logError("Error getting Python", error, "INIT_PYTHON_ERR");
        throw error;
    }

    OUTPUT_CHANNEL.appendLine("Using python executable: " + executableAndEnv.pythonExe);

    let port: number = roboConfig.getLanguageServerTcpPort();
    if (port) {
        // For TCP server needs to be started seperately
        OUTPUT_CHANNEL.appendLine("Connecting to language server in port: " + port);
        return new Promise((resolve, reject) => {
            var client = new net.Socket();
            client.setTimeout(2000, reject);
            try {
                client.connect(port, "127.0.0.1", function () {
                    resolve({
                        reader: client,
                        writer: client,
                    });
                });
            } catch (error) {
                reject(error);
            }
        });
    } else {
        let targetFile: string = getExtensionRelativeFile("../../src/robocorp_code/__main__.py");
        if (!targetFile) {
            OUTPUT_CHANNEL.appendLine("Error resolving ../../src/robocorp_code/__main__.py");
            C.useErrorStubs = true;
            notifyOfInitializationErrorShowOutputTab();
            feedbackRobocorpCodeError("INIT_MAIN_NOT_FOUND");
            return;
        }

        let args: Array<string> = ["-u", targetFile];
        let lsArgs = roboConfig.getLanguageServerArgs();
        if (lsArgs && lsArgs.length >= 1) {
            args = args.concat(lsArgs);
        } else {
            // Default is using simple verbose mode (shows critical/info but not debug).
            args = args.concat(["-v"]);
        }

        OUTPUT_CHANNEL.appendLine(
            "Starting Robocorp Code with args: " + executableAndEnv.pythonExe + " " + args.join(" ")
        );

        let src: string = path.resolve(__dirname, "../../src");
        let executableAndEnvEnviron = {};
        if (executableAndEnv.environ) {
            executableAndEnvEnviron = executableAndEnv.environ;
        }

        let finalEnv = mergeEnviron({ ...executableAndEnvEnviron, PYTHONPATH: src });
        const serverProcess = cp.spawn(executableAndEnv.pythonExe, args, {
            env: finalEnv,
            cwd: path.dirname(executableAndEnv.pythonExe),
        });
        if (!serverProcess || !serverProcess.pid) {
            throw new Error(`Launching server using command ${executableAndEnv.pythonExe} with args: ${args} failed.`);
        }
        return serverProcess;
    }
};

async function notifyOfInitializationErrorShowOutputTab(msg?: string) {
    OUTPUT_CHANNEL.show();
    if (!msg) {
        msg = "Unable to activate Robocorp Code extension. Please see: Output > Robocorp Code for more details.";
    }
    window.showErrorMessage(msg);
    const selection = await window.showErrorMessage(msg, "Show Output > Robocorp Code");
    if (selection) {
        OUTPUT_CHANNEL.show();
    }
}

class CommandRegistry {
    private context: ExtensionContext;
    public registerErrorStubs: boolean = false;
    public useErrorStubs: boolean = false;
    public errorMessage: string | undefined = undefined;

    public constructor(context: ExtensionContext) {
        this.context = context;
    }

    public registerWithoutStub(command: string, callback: (...args: any[]) => any, thisArg?: any): void {
        this.context.subscriptions.push(commands.registerCommand(command, callback));
    }

    /**
     * Registers with a stub so that an error may be shown if the initialization didn't work.
     */
    public register(command: string, callback: (...args: any[]) => any, thisArg?: any): void {
        const that = this;
        async function redirect() {
            if (that.useErrorStubs) {
                notifyOfInitializationErrorShowOutputTab(that.errorMessage);
            } else {
                return await callback.apply(thisArg, arguments);
            }
        }

        this.context.subscriptions.push(commands.registerCommand(command, redirect));
    }
}

async function verifyRobotFrameworkInstalled() {
    if (!roboConfig.getVerifylsp()) {
        return;
    }
    const ROBOT_EXTENSION_ID = "robocorp.robotframework-lsp";
    let found = true;
    try {
        let extension = extensions.getExtension(ROBOT_EXTENSION_ID);
        if (!extension) {
            found = false;
        }
    } catch (error) {
        found = false;
    }
    if (!found) {
        // It seems it's not installed, install?
        let install = "Install";
        let dontAsk = "Don't ask again";
        let chosen = await window.showInformationMessage(
            "It seems that the Robot Framework Language Server extension is not installed to work with .robot Files.",
            install,
            dontAsk
        );
        if (chosen == install) {
            await commands.executeCommand("workbench.extensions.search", ROBOT_EXTENSION_ID);
        } else if (chosen == dontAsk) {
            roboConfig.setVerifylsp(false);
        }
    }
}

async function cloudLoginShowConfirmationAndRefresh() {
    let loggedIn = await cloudLogin();
    if (loggedIn) {
        window.showInformationMessage("Successfully logged in Control Room.");
    }
    refreshCloudTreeView();
}

async function cloudLogoutAndRefresh() {
    await cloudLogout();
    refreshCloudTreeView();
}

async function convertProject() {
    const DEFAULT_ERROR_MSG = `
            Could not convert project.
            Please check the output logs for more details.
            `;
    const DEFAULT_ERROR_STATUS = "Error while converting project.";

    const convertBundlePromise = ensureConvertBundle();

    const fileToConvert: Uri[] = await window.showOpenDialog({
        "canSelectFolders": false,
        "canSelectFiles": true,
        "canSelectMany": false,
        "openLabel": "Select file to convert to Robocorp Robot",
    });
    if (!fileToConvert || fileToConvert.length === 0) {
        return;
    }
    const uri = fileToConvert[0];

    try {
        const converterLocation = await convertBundlePromise;
        if (!converterLocation) {
            throw new Error("There was an issue downloading the converter bundle. Please try again.");
        }
        const converterBundle = require(converterLocation);

        // let the user decide what type of project will be converted
        const vendorMap = {
            "Blue Prism": "blueprism",
            "UiPath": "uipath",
            "Automation Anywhere 360": "a360",
        };
        const items = Object.keys(vendorMap);
        const selectedFormat = await window.showQuickPick(items, {
            "placeHolder": `Please select the file format of ${path.basename(uri.fsPath)} `,
            "canPickMany": false,
            "ignoreFocusOut": true,
        });
        if (!selectedFormat) {
            // exit conversion if there is no format selected
            return;
        }
        // let the user decide where the conversion result will be saved
        const wsFolders: ReadonlyArray<WorkspaceFolder> = workspace.workspaceFolders;
        let ws: WorkspaceFolder;
        if (wsFolders.length == 1) {
            ws = wsFolders[0];
        } else {
            ws = await window.showWorkspaceFolderPick({
                "placeHolder": "Please select the workspace folder for the conversion output",
                "ignoreFocusOut": true,
            });
        }
        if (!ws) {
            // exit conversion if there is no workspace
            return;
        }
        const destination = Uri.joinPath(ws.uri, "converted");

        // actual conversion
        const bytes = await workspace.fs.readFile(uri);
        const contents = new TextDecoder("utf-8").decode(bytes);
        const home = roboConfig.getHome();
        const options = {
            // objectImplFile: workspace.fs.path(home, 'converter/blueprism/robocorp-commons/convert.yaml')
        };
        const conversionResult: ConversionResult = await converterBundle.convert(vendorMap[selectedFormat], contents, options);
        if (!converterBundle.isSuccessful(conversionResult)) {
            logError(
                "Error converting file to Robocorp Robot",
                new Error((<ConversionFailure>conversionResult).error),
                "EXT_CONVERT_PROJECT"
            );
            window.showErrorMessage(DEFAULT_ERROR_MSG);
            OUTPUT_CHANNEL.show();
            return;
        }
        const populate_action: ActionResult<string> = await commands.executeCommand(
            "robocorp.saveConvertedProject.internal",
            {
                "destinationFolderURI": destination.toString(),
                "conversionResult": conversionResult,
                "projectSourceVendor": vendorMap[selectedFormat],
            }
        );
        if (!populate_action.success) {
            throw new Error(populate_action.message);
        }
        window.showInformationMessage("Project conversion succeeded, saved inside ${workspace}/converted.");
    } catch (err) {
        logError(DEFAULT_ERROR_STATUS, err, "EXT_CONVERT_PROJECT");
        window.showErrorMessage(DEFAULT_ERROR_MSG);
        OUTPUT_CHANNEL.show();
        return;
    }
}

function registerRobocorpCodeCommands(C: CommandRegistry) {
    C.register(ROBOCORP_GET_LANGUAGE_SERVER_PYTHON, () => getLanguageServerPython());
    C.register(ROBOCORP_GET_LANGUAGE_SERVER_PYTHON_INFO, () => getLanguageServerPythonInfo());
    C.register(ROBOCORP_CREATE_ROBOT, () => createRobot());
    C.register(ROBOCORP_UPLOAD_ROBOT_TO_CLOUD, () => uploadRobot());
    C.register(ROBOCORP_CONFIGURATION_DIAGNOSTICS, () => rccConfigurationDiagnostics());
    C.register(ROBOCORP_RUN_ROBOT_RCC, () => askAndRunRobotRCC(true));
    C.register(ROBOCORP_DEBUG_ROBOT_RCC, () => askAndRunRobotRCC(false));
    C.register(ROBOCORP_SET_PYTHON_INTERPRETER, () => setPythonInterpreterFromRobotYaml());
    C.register(ROBOCORP_REFRESH_ROBOTS_VIEW, () => refreshTreeView(TREE_VIEW_ROBOCORP_ROBOTS_TREE));
    C.register(ROBOCORP_REFRESH_CLOUD_VIEW, () => refreshCloudTreeView());
    C.register(ROBOCORP_ROBOTS_VIEW_TASK_RUN, (entry: RobotEntry) => views.runSelectedRobot(true, entry));
    C.register(ROBOCORP_ROBOTS_VIEW_TASK_DEBUG, (entry: RobotEntry) => views.runSelectedRobot(false, entry));
    C.register(ROBOCORP_EDIT_ROBOCORP_INSPECTOR_LOCATOR, (locator?: LocatorEntry) =>
        inspector.openRobocorpInspector(undefined, locator)
    );
    C.register(ROBOCORP_NEW_ROBOCORP_INSPECTOR_BROWSER, () => inspector.openRobocorpInspector("browser"));
    C.register(ROBOCORP_NEW_ROBOCORP_INSPECTOR_IMAGE, () => inspector.openRobocorpInspector("image"));
    C.register(ROBOCORP_NEW_ROBOCORP_INSPECTOR_WINDOWS, () => inspector.openRobocorpInspector("windows"));
    C.register(ROBOCORP_COPY_LOCATOR_TO_CLIPBOARD_INTERNAL, (locator?: LocatorEntry) =>
        copySelectedToClipboard(locator)
    );
    C.register(ROBOCORP_REMOVE_LOCATOR_FROM_JSON, (locator?: LocatorEntry) => removeLocator(locator));
    C.register(ROBOCORP_OPEN_ROBOT_TREE_SELECTION, (robot: RobotEntry) => views.openRobotTreeSelection(robot));
    C.register(ROBOCORP_OPEN_ROBOT_CONDA_TREE_SELECTION, (robot: RobotEntry) =>
        views.openRobotCondaTreeSelection(robot)
    );
    C.register(ROBOCORP_OPEN_LOCATORS_JSON, (locatorRoot) => views.openLocatorsJsonTreeSelection());
    C.register(ROBOCORP_CLOUD_UPLOAD_ROBOT_TREE_SELECTION, (robot: RobotEntry) =>
        views.cloudUploadRobotTreeSelection(robot)
    );
    C.register(ROBOCORP_OPEN_FLOW_EXPLORER_TREE_SELECTION, (robot: RobotEntry) =>
        commands.executeCommand("robot.openFlowExplorer", Uri.file(robot.robot.directory).toString())
    );
    C.register(ROBOCORP_CONVERT_PROJECT, async () => convertProject());
    C.register(ROBOCORP_CREATE_RCC_TERMINAL_TREE_SELECTION, (robot: RobotEntry) =>
        views.createRccTerminalTreeSelection(robot)
    );
    C.register(ROBOCORP_RCC_TERMINAL_NEW, () => askAndCreateRccTerminal());
    C.register(ROBOCORP_REFRESH_ROBOT_CONTENT_VIEW, () => refreshTreeView(TREE_VIEW_ROBOCORP_ROBOT_CONTENT_TREE));
    C.register(ROBOCORP_NEW_FILE_IN_ROBOT_CONTENT_VIEW, newFileInRobotContentTree);
    C.register(ROBOCORP_NEW_FOLDER_IN_ROBOT_CONTENT_VIEW, newFolderInRobotContentTree);
    C.register(ROBOCORP_DELETE_RESOURCE_IN_ROBOT_CONTENT_VIEW, deleteResourceInRobotContentTree);
    C.register(ROBOCORP_RENAME_RESOURCE_IN_ROBOT_CONTENT_VIEW, renameResourceInRobotContentTree);
    C.register(ROBOCORP_UPDATE_LAUNCH_ENV, updateLaunchEnvironment);
    C.register(ROBOCORP_CONNECT_VAULT, connectVault);
    C.register(ROBOCORP_DISCONNECT_VAULT, disconnectVault);
    C.register(ROBOCORP_OPEN_CLOUD_HOME, async () => {
        const cloudBaseUrl = await getEndpointUrl("cloud-ui");
        commands.executeCommand("vscode.open", Uri.parse(cloudBaseUrl + "home"));
    });
    C.register(ROBOCORP_OPEN_VAULT_HELP, async () => {
        const cloudBaseUrl = await getEndpointUrl("docs");
        commands.executeCommand(
            "vscode.open",
            Uri.parse(cloudBaseUrl + "development-guide/variables-and-secrets/vault")
        );
    });
    C.register(ROBOCORP_OPEN_EXTERNALLY, async (item: FSEntry) => {
        if (item.filePath) {
            if (await fileExists(item.filePath)) {
                env.openExternal(Uri.file(item.filePath));
                return;
            }
        }
        window.showErrorMessage("Unable to open: " + item.filePath + " (file does not exist).");
    });
    C.register(ROBOCORP_OPEN_IN_VS_CODE, async (item: FSEntry) => {
        if (item.filePath) {
            if (await fileExists(item.filePath)) {
                commands.executeCommand("vscode.open", Uri.file(item.filePath));
                return;
            }
        }
        window.showErrorMessage("Unable to open: " + item.filePath + " (file does not exist).");
    });
    C.register(ROBOCORP_REVEAL_IN_EXPLORER, async (item: FSEntry) => {
        if (item.filePath) {
            if (await fileExists(item.filePath)) {
                commands.executeCommand("revealFileInOS", Uri.file(item.filePath));
                return;
            }
        }
        window.showErrorMessage("Unable to reveal in explorer: " + item.filePath + " (file does not exist).");
    });
    C.register(ROBOCORP_REVEAL_ROBOT_IN_EXPLORER, async (item: RobotEntry) => {
        if (item.uri) {
            if (await uriExists(item.uri)) {
                commands.executeCommand("revealFileInOS", item.uri);
                return;
            }
        }
        window.showErrorMessage("Unable to reveal in explorer: " + item.uri + " (Robot does not exist).");
    });
    C.register(ROBOCORP_CONVERT_OUTPUT_WORK_ITEM_TO_INPUT, convertOutputWorkItemToInput);
    C.register(ROBOCORP_CLOUD_LOGIN, () => cloudLoginShowConfirmationAndRefresh());
    C.register(ROBOCORP_CLOUD_LOGOUT, () => cloudLogoutAndRefresh());
    C.register(ROBOCORP_NEW_WORK_ITEM_IN_WORK_ITEMS_VIEW, newWorkItemInWorkItemsTree);
    C.register(ROBOCORP_DELETE_WORK_ITEM_IN_WORK_ITEMS_VIEW, deleteWorkItemInWorkItemsTree);
    C.register(ROBOCORP_HELP_WORK_ITEMS, openWorkItemHelp);
}

async function clearEnvAndRestart() {
    await window.withProgress(
        {
            location: vscode.ProgressLocation.Window,
            title: "Clearing environments and restarting Robocorp Code.",
            cancellable: false,
        },
        clearEnvsAndRestart
    );
}

async function clearEnvsAndRestart(progress: vscode.Progress<{ message?: string; increment?: number }>) {
    let allOk: boolean = true;
    let okToRestartRFLS = false;
    try {
        await langServerMutex.dispatch(async () => {
            let result = await clearEnvsLocked(progress);
            if (!result) {
                // Something didn't work out...
                return;
            }
            okToRestartRFLS = result["okToRestartRFLS"];
        });
        const timing = new Timing();
        progress.report({
            "message": `Waiting for Robocorp Code to be ready.`,
        });
        await langServer.onReady();
        let msg = "Restarted Robocorp Code. Took: " + timing.getTotalElapsedAsStr();
        progress.report({
            "message": msg,
        });
        OUTPUT_CHANNEL.appendLine(msg);
    } catch (err) {
        allOk = false;
        const msg = "Error restarting Robocorp Code";
        notifyOfInitializationErrorShowOutputTab(msg);
        logError(msg, err, "INIT_RESTART_ROBOCORP_CODE");
    } finally {
        if (allOk) {
            window.showInformationMessage("RCC Environments cleared and Robocorp Code restarted.");
            C.useErrorStubs = false;
        } else {
            C.useErrorStubs = true;
        }

        if (okToRestartRFLS) {
            progress.report({
                "message": `Starting Robot Framework Language Server.`,
            });
            await commands.executeCommand("robot.clearCachesAndRestartProcesses.finish.internal");
        }
    }
}

async function clearEnvsLocked(progress: vscode.Progress<{ message?: string; increment?: number }>) {
    const rccLocation = await getRccLocation();
    if (!rccLocation) {
        let msg = "Unable to clear caches because RCC is not available.";
        OUTPUT_CHANNEL.appendLine(msg);
        window.showErrorMessage(msg);
        return undefined;
    }

    const robocorpHome = await getRobocorpHome();
    progress.report({
        "message": `Computing environments to collect.`,
    });
    const envsToLoCollect = await computeEnvsToCollect(rccLocation, robocorpHome);

    // Clear our cache since we're killing that environment...
    globalCachedPythonInfo = undefined;

    C.useErrorStubs = true; // Prevent any calls while restarting...
    C.errorMessage = "Unable to use Robocorp Code actions while clearing environments.";
    let okToRestartRFLS = false;
    try {
        let timing = new Timing();
        const extension = extensions.getExtension("robocorp.robotframework-lsp");
        if (extension) {
            progress.report({
                "message": `Stopping Robot Framework Language Server.`,
            });
            // In this case we also need to stop the language server.
            okToRestartRFLS = await commands.executeCommand("robot.clearCachesAndRestartProcesses.start.internal");
            OUTPUT_CHANNEL.appendLine(
                "Stopped Robot Framework Language Server. Took: " + timing.getTotalElapsedAsStr()
            );
        }

        let timingStop = new Timing();
        progress.report({
            "message": `Stopping Robocorp Code.`,
        });
        await langServer.stop();
        OUTPUT_CHANNEL.appendLine("Stopped Robocorp Code. Took: " + timingStop.getTotalElapsedAsStr());

        if (envsToLoCollect) {
            await clearRCCEnvironments(rccLocation, robocorpHome, envsToLoCollect, progress);
        }

        try {
            progress.report({
                "message": `Clearing Robocorp Code caches.`,
            });
            await clearRobocorpCodeCaches(robocorpHome);
        } catch (error) {
            let msg = "Error clearing Robocorp Code caches.";
            logError(msg, error, "RCC_CLEAR_ENV");
        }

        progress.report({
            "message": `Starting Robocorp Code.`,
        });
        langServer.start();
    } finally {
        C.errorMessage = undefined;
    }
    return { "okToRestartRFLS": okToRestartRFLS };
}

let langServer: LanguageClient;
let C: CommandRegistry;
export let globalCachedPythonInfo: InterpreterInfo;
const langServerMutex: Mutex = new Mutex();

export async function activate(context: ExtensionContext) {
    let timing = new Timing();
    OUTPUT_CHANNEL.appendLine("Activating Robocorp Code extension.");
    C = new CommandRegistry(context);

    try {
        return await langServerMutex.dispatch(async () => {
            let ret = await doActivate(context, C);
            OUTPUT_CHANNEL.appendLine("Robocorp Code initialization finished. Took: " + timing.getTotalElapsedAsStr());
            return ret;
        });
    } catch (error) {
        logError("Error initializing Robocorp Code extension", error, "INIT_ROBOCORP_CODE_ERROR");
        C.useErrorStubs = true;
        notifyOfInitializationErrorShowOutputTab();
    }
}

interface ExecuteWorkspaceCommandArgs {
    command: string;
    arguments: any;
}

export async function doActivate(context: ExtensionContext, C: CommandRegistry) {
    // Note: register the submit issue actions early on so that we can later actually
    // report startup errors.
    C.registerWithoutStub(ROBOCORP_SUBMIT_ISSUE, async () => {
        await showSubmitIssueUI(context);
    });

    // i.e.: allow other extensions to also use our submit issue api.
    C.registerWithoutStub(
        ROBOCORP_SUBMIT_ISSUE_INTERNAL,
        (
            dialogMessage: string,
            email: string,
            errorName: string,
            errorCode: string,
            errorMessage: string,
            files: string[]
        ) => submitIssue(dialogMessage, email, errorName, errorCode, errorMessage, files)
    );

    C.registerWithoutStub(ROBOCORP_SHOW_OUTPUT, () => OUTPUT_CHANNEL.show());
    C.registerWithoutStub(ROBOCORP_SHOW_INTERPRETER_ENV_ERROR, async (params) => {
        const fileWithError = params.fileWithError;
        vscode.window.showTextDocument(Uri.file(fileWithError));
    });

    // i.e.: allow other extensions to also use our error feedback api.
    C.registerWithoutStub(ROBOCORP_ERROR_FEEDBACK_INTERNAL, (errorSource: string, errorCode: string) =>
        feedbackAnyError(errorSource, errorCode)
    );
    // i.e.: allow other extensions to also use our feedback api.
    C.registerWithoutStub(ROBOCORP_FEEDBACK_INTERNAL, (name: string, value: string) => feedback(name, value));

    C.registerWithoutStub(ROBOCORP_CLEAR_ENV_AND_RESTART, clearEnvAndRestart);
    // Register other commands (which will have an error message shown depending on whether
    // the extension was activated properly).
    registerRobocorpCodeCommands(C);

    const extension = extensions.getExtension("robocorp.robotframework-lsp");
    if (extension) {
        // If the Robot Framework Language server is present, make sure it is compatible with this
        // version.
        try {
            const version: string = extension.packageJSON.version;
            const splitted = version.split(".");
            const major = parseInt(splitted[0]);
            const minor = parseInt(splitted[1]);
            const micro = parseInt(splitted[2]);
            if (major < 1 || (major == 1 && (minor < 1 || (minor == 1 && micro < 1)))) {
                const msg =
                    "Unable to initialize the Robocorp Code extension because the Robot Framework Language Server version (" +
                    version +
                    ") is not compatible with this version of Robocorp Code. Robot Framework Language Server 1.1.1 or newer is required. Please update to proceed. ";
                OUTPUT_CHANNEL.appendLine(msg);
                C.useErrorStubs = true;
                notifyOfInitializationErrorShowOutputTab(msg);
                return;
            }
        } catch (err) {
            logError("Error verifying Robot Framework Language Server version.", err, "INIT_RF_TOO_OLD");
        }
    }

    workspace.onDidChangeConfiguration((event) => {
        for (let s of [
            roboConfig.ROBOCORP_LANGUAGE_SERVER_ARGS,
            roboConfig.ROBOCORP_LANGUAGE_SERVER_PYTHON,
            roboConfig.ROBOCORP_LANGUAGE_SERVER_TCP_PORT,
        ]) {
            if (event.affectsConfiguration(s)) {
                window
                    .showWarningMessage(
                        'Please use the "Reload Window" action for changes in ' + s + " to take effect.",
                        ...["Reload Window"]
                    )
                    .then((selection) => {
                        if (selection === "Reload Window") {
                            commands.executeCommand("workbench.action.reloadWindow");
                        }
                    });
                return;
            }
        }
    });

    let startLsTiming = new Timing();
    langServer = new LanguageClient("Robocorp Code", serverOptions, clientOptions);

    context.subscriptions.push(
        langServer.onDidChangeState((event) => {
            if (event.newState == State.Running) {
                // i.e.: We need to register the customProgress as soon as it's running (we can't wait for onReady)
                // because at that point if there are open documents, lots of things may've happened already, in
                // which case the progress won't be shown on some cases where it should be shown.
                context.subscriptions.push(
                    langServer.onNotification("$/customProgress", (args: ProgressReport) => {
                        // OUTPUT_CHANNEL.appendLine(args.id + " - " + args.kind + " - " + args.title + " - " + args.message + " - " + args.increment);
                        let progressReporter = handleProgressMessage(args);
                        if (progressReporter) {
                            if (args.kind == "begin") {
                                const progressId = args.id;
                                progressReporter.token.onCancellationRequested(() => {
                                    langServer.sendNotification("cancelProgress", { progressId: progressId });
                                });
                            }
                        }
                    })
                );
                context.subscriptions.push(
                    langServer.onNotification("$/linkedAccountChanged", () => {
                        refreshCloudTreeView();
                    })
                );
                context.subscriptions.push(
                    langServer.onRequest("$/executeWorkspaceCommand", async (args: ExecuteWorkspaceCommandArgs) => {
                        // OUTPUT_CHANNEL.appendLine(args.command + " - " + args.arguments);
                        let ret;
                        try {
                            ret = await commands.executeCommand(args.command, args.arguments);
                        } catch (err) {
                            if (!(err.message && err.message.endsWith("not found"))) {
                                // Log if the error wasn't that the command wasn't found
                                logError("Error executing workspace command.", err, "EXT_EXECUTE_WS_COMMAND");
                            }
                        }
                        return ret;
                    })
                );
            }
        })
    );
    views.registerViews(context);
    registerDebugger();

    try {
        let disposable: Disposable = langServer.start();
        context.subscriptions.push(disposable);
        // i.e.: if we return before it's ready, the language server commands
        // may not be available.
        OUTPUT_CHANNEL.appendLine("Waiting for Robocorp Code (python) language server to finish activating...");
        await langServer.onReady();
        OUTPUT_CHANNEL.appendLine(
            "Took: " + startLsTiming.getTotalElapsedAsStr() + " to initialize Robocorp Code Language Server."
        );
    } catch (error) {
        logError("Error initializing Robocorp code.", error, "ERROR_INITIALIZING_ROBOCORP_CODE_LANG_SERVER");
    }

    // Note: start the async ones below but don't await on them (the extension should be considered initialized
    // regardless of it -- as it may call robot.resolveInterpreter, it may need to activate the language
    // server extension, which in turn requires robocorp code to be activated already).
    installPythonInterpreterCheck(context);
    verifyRobotFrameworkInstalled();
}

export function deactivate(): Thenable<void> | undefined {
    if (!langServer) {
        return undefined;
    }
    return langServer.stop();
}

async function getLanguageServerPython(): Promise<string | undefined> {
    let info = await getLanguageServerPythonInfo();
    if (!info) {
        return undefined;
    }
    return info.pythonExe;
}

export async function getLanguageServerPythonInfo(): Promise<InterpreterInfo | undefined> {
    if (globalCachedPythonInfo) {
        return globalCachedPythonInfo;
    }
    let cachedPythonInfo = await getLanguageServerPythonInfoUncached();
    if (!cachedPythonInfo) {
        return undefined; // Unable to get it.
    }
    // Ok, we got it (cache that info).
    globalCachedPythonInfo = cachedPythonInfo;
    return globalCachedPythonInfo;
}
