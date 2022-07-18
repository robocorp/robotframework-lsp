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
import { getAutosetpythonextensioninterpreter } from "./robocorpSettings";

export async function autoUpdateInterpreter(docUri: Uri) {
    if (!getAutosetpythonextensioninterpreter()) {
        return;
    }
    let result: ActionResult<InterpreterInfo | undefined> = await resolveInterpreter(docUri.fsPath);
    if (!result.success) {
        return;
    }
    let interpreter: InterpreterInfo = result.result;
    if (!interpreter || !interpreter.pythonExe) {
        return;
    }

    // Now, set the interpreter.
    let pythonExecutable = await getPythonExecutable(docUri, true, false);
    if (pythonExecutable != interpreter.pythonExe) {
        setPythonInterpreterForPythonExtension(interpreter.pythonExe, docUri);
    }
}

export async function installPythonInterpreterCheck(context: ExtensionContext) {
    context.subscriptions.push(
        window.onDidChangeActiveTextEditor(async (event: TextEditor) => {
            try {
                // Whenever the active editor changes we update the Python interpreter used (if needed).
                let docUri = event?.document?.uri;
                if (docUri) {
                    await autoUpdateInterpreter(docUri);
                }
            } catch (error) {
                logError("Error auto-updating Python interpreter.", error, "PYTHON_SET_INTERPRETER");
            }
        })
    );
    try {
        let uri = window.activeTextEditor?.document?.uri;
        if (uri) {
            await autoUpdateInterpreter(uri);
        }
    } catch (error) {
        logError("Error on initial Python interpreter auto-update.", error, "PYTHON_INITIAL_SET_INTERPRETER");
    }
}

export async function disablePythonTerminalActivateEnvironment() {
    try {
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
