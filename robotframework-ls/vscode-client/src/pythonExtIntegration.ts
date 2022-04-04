import { extensions, Uri, workspace } from "vscode";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { handleProgressMessage } from "./progress";

export async function getPythonExtensionExecutable(
    resource: Uri = null,
    showInOutput: boolean = true
): Promise<string[] | undefined> {
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
                OUTPUT_CHANNEL.appendLine("vscode-python execCommand: " + execCommand);
            }
            if (!execCommand) {
                OUTPUT_CHANNEL.appendLine("vscode-python did not return proper execution details.");
                return undefined;
            }
            if (execCommand instanceof Array) {
                if (execCommand.length === 0) {
                    return undefined;
                }
                return execCommand;
            }
            return [execCommand];
        } else {
            let config = workspace.getConfiguration("python");
            let executable = <string>await config.get("defaultInterpreterPath");
            if (!executable) {
                return undefined;
            }
            return [executable];
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
