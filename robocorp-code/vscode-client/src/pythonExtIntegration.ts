import {
    commands,
    ConfigurationTarget,
    ExtensionContext,
    extensions,
    TextEditor,
    Uri,
    window,
    workspace,
} from "vscode";
import { resolveInterpreter } from "./activities";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { handleProgressMessage } from "./progress";
import { ActionResult, InterpreterInfo } from "./protocols";
import { getAutosetpythonextensioninterpreter } from "./robocorpSettings";
import { TREE_VIEW_ROBOCORP_TASK_PACKAGES_TREE } from "./robocorpViews";
import { refreshTreeView } from "./viewsCommon";

const dirtyWorkspaceFiles = new Set<string>();

export function isEnvironmentFile(fsPath: string): boolean {
    return (
        fsPath.endsWith("conda.yaml") ||
        fsPath.endsWith("action-server.yaml") ||
        fsPath.endsWith("package.yaml") ||
        fsPath.endsWith("robot.yaml")
    );
}

export function isPythonFile(fsPath: string): boolean {
    return fsPath.endsWith(".py");
}

export async function autoUpdateInterpreter(docUri: Uri): Promise<boolean> {
    if (!getAutosetpythonextensioninterpreter()) {
        return false;
    }
    let result: ActionResult<InterpreterInfo | undefined> = await resolveInterpreter(docUri.fsPath);
    if (!result.success) {
        return false;
    }
    let interpreter: InterpreterInfo = result.result;
    if (!interpreter || !interpreter.pythonExe) {
        return false;
    }

    // Now, set the interpreter.
    let pythonExecutable = await getPythonExecutable(docUri, true, false);
    if (pythonExecutable != interpreter.pythonExe) {
        setPythonInterpreterForPythonExtension(interpreter.pythonExe, docUri);
    }

    const additional = interpreter.additionalPythonpathEntries;
    if (additional && additional.length > 0) {
        workspace.getConfiguration("python", docUri).update(
            "analysis.extraPaths",
            additional.map((el) => {
                return el.replaceAll("\\", "/");
            }),
            ConfigurationTarget.WorkspaceFolder
        );
    }
    return true;
}

export async function installWorkspaceWatcher(context: ExtensionContext) {
    // listen to editor change/switch (this should cause environment switching as well)
    const checkEditorSwitch = window.onDidChangeActiveTextEditor(async (event: TextEditor) => {
        try {
            // Whenever the active editor changes we update the Python interpreter used (if needed).
            let docURI = event?.document?.uri;
            if (docURI) {
                await autoUpdateInterpreter(docURI);
            }
        } catch (error) {
            logError("Error auto-updating Python interpreter.", error, "PYTHON_SET_INTERPRETER");
        }
    });

    // listen for document changes and mark targeted files as dirty
    const checkIfFilesHaveChanged = workspace.onDidChangeTextDocument(async (event) => {
        let docURI = event.document.uri;
        if (event.document.isDirty && (isEnvironmentFile(docURI.fsPath) || isPythonFile(docURI.fsPath))) {
            dirtyWorkspaceFiles.add(docURI.fsPath);
        }
    });

    // listen for when documents are saved and check if the files of interest have changed
    const checkIfFilesWillBeSaved = workspace.onDidSaveTextDocument(async (document) => {
        try {
            let docURI = document.uri;
            if (
                docURI &&
                dirtyWorkspaceFiles.has(docURI.fsPath) &&
                (isEnvironmentFile(docURI.fsPath) || isPythonFile(docURI.fsPath))
            ) {
                // let's refresh the view each time we get a hit on the files that might impact the workspace
                refreshTreeView(TREE_VIEW_ROBOCORP_TASK_PACKAGES_TREE);
                dirtyWorkspaceFiles.delete(docURI.fsPath);
                // if environment file has changed, let's ask the user if he wants to update the env
                if (isEnvironmentFile(docURI.fsPath)) {
                    window
                        .showInformationMessage(
                            "Changes were detected in the package configuration. Would you like to rebuild the environment?",
                            "Yes",
                            "No"
                        )
                        .then(async (selection) => {
                            if (selection === "Yes") {
                                const result = await autoUpdateInterpreter(docURI);
                                if (result) {
                                    window.showInformationMessage(
                                        `Environment built & cached. Python interpreter loaded.`
                                    );
                                } else {
                                    window.showErrorMessage(`Failed to Auto Update the Python Interpreter`);
                                }
                            }
                        });
                }
            }
        } catch (error) {
            logError("Error auto-updating Python interpreter.", error, "PYTHON_SET_INTERPRETER");
        }
    });
    // create the appropriate subscriptions
    context.subscriptions.push(checkEditorSwitch, checkIfFilesHaveChanged, checkIfFilesWillBeSaved);

    // update the interpreter at start time
    try {
        let docURI = window.activeTextEditor?.document?.uri;
        if (docURI) {
            await autoUpdateInterpreter(docURI);
        }
    } catch (error) {
        logError("Error on initial Python interpreter auto-update.", error, "PYTHON_INITIAL_SET_INTERPRETER");
    }
}

export async function disablePythonTerminalActivateEnvironment() {
    try {
        const extension = extensions.getExtension("ms-python.python");
        if (!extension) {
            return;
        }

        let configurationTarget: ConfigurationTarget = ConfigurationTarget.Workspace;
        let config = workspace.getConfiguration("python");
        await config.update("terminal.activateEnvironment", false, configurationTarget);
    } catch (error) {
        logError(
            "Error disabling python terminal activate environment.",
            error,
            "PYTHON_DISABLE_TERMINAL_ACTIVATE_ENVIRONMENT"
        );
    }
}

export async function setPythonInterpreterForPythonExtension(pythonExe: string, uri: Uri) {
    const extension = extensions.getExtension("ms-python.python");
    if (!extension) {
        return;
    }

    // Note: always set it in the workspace!
    let configurationTarget: ConfigurationTarget = ConfigurationTarget.Workspace;

    OUTPUT_CHANNEL.appendLine("Setting the python executable path for vscode-python to be:\n" + pythonExe);
    if (extension?.exports?.environment?.setActiveEnvironment !== undefined) {
        await extension.exports.environment.setActiveEnvironment(pythonExe, uri);
        // OUTPUT_CHANNEL.appendLine("Is: " + (await extension.exports.environment.getActiveInterpreterPath(uri)));
    } else {
        if (extension?.exports?.environment?.setActiveInterpreter !== undefined) {
            await extension.exports.environment.setActiveInterpreter(pythonExe, uri);
            // OUTPUT_CHANNEL.appendLine("Is: " + (await extension.exports.environment.getActiveInterpreterPath(uri)));
        } else {
            let config = workspace.getConfiguration("python");
            await config.update("defaultInterpreterPath", pythonExe, configurationTarget);

            try {
                await commands.executeCommand("python.clearWorkspaceInterpreter");
            } catch (err) {
                logError(
                    "Error calling python.clearWorkspaceInterpreter",
                    err,
                    "ACT_CLEAR_PYTHON_WORKSPACE_INTERPRETER"
                );
            }
        }
    }
}

export async function getPythonExecutable(
    resource: Uri = null,
    forceLoadFromConfig: boolean = false,
    showInOutput: boolean = true
): Promise<string | undefined | "config"> {
    try {
        const extension = extensions.getExtension("ms-python.python");
        if (!extension) {
            OUTPUT_CHANNEL.appendLine(
                "Unable to get python executable from vscode-python. ms-python.python extension not found."
            );
            return undefined;
        }

        const usingNewInterpreterStorage = extension.packageJSON?.featureFlags?.usingNewInterpreterStorage;
        if (usingNewInterpreterStorage) {
            // Note: just this in not enough to know if the user is actually using the new API
            // (i.e.: he may not be in the experiment).
            if (!extension.isActive) {
                const id = "activate-vscode-python-" + Date.now();
                handleProgressMessage({
                    kind: "begin",
                    id: id,
                    title: "Waiting for vscode-python activation...",
                });
                try {
                    await extension.activate();
                } finally {
                    handleProgressMessage({
                        kind: "end",
                        id: id,
                    });
                }
            }
            let execCommand = extension.exports.settings.getExecutionDetails(resource).execCommand;
            if (showInOutput) {
                OUTPUT_CHANNEL.appendLine("vscode-python execution details: " + execCommand);
            }
            if (!execCommand) {
                OUTPUT_CHANNEL.appendLine("vscode-python did not return proper execution details.");
                return undefined;
            }
            if (execCommand instanceof Array) {
                // It could be some composite command such as conda activate, but that's ok, we don't want to consider those
                // a match for our use-case.
                return execCommand.join(" ");
            }
            return execCommand;
        } else {
            // Not using new interpreter storage (so, it should be queried from the settings).
            if (!forceLoadFromConfig) {
                return "config";
            }
            let config = workspace.getConfiguration("python");
            return await config.get("defaultInterpreterPath");
        }
    } catch (error) {
        logError(
            "Error when querying about python executable path from vscode-python.",
            error,
            "PYTHON_EXT_NO_PYTHON_EXECUTABLE"
        );
        return undefined;
    }
}
