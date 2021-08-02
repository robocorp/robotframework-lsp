import { extensions, Uri } from "vscode";
import { OUTPUT_CHANNEL } from "./channel";
import { handleProgressMessage } from "./progress";

export async function getPythonExecutable(resource: Uri = null): Promise<string | undefined | 'config'> {
    try {
        const extension = extensions.getExtension("ms-python.python");
        if (!extension) {
            OUTPUT_CHANNEL.appendLine('Unable to get python executable from vscode-python. ms-python.python extension not found.')
            return undefined;
        }

        const usingNewInterpreterStorage = extension.packageJSON?.featureFlags?.usingNewInterpreterStorage;
        if (usingNewInterpreterStorage) {
            // Note: just this in not enough to know if the user is actually using the new API
            // (i.e.: he may not be in the experiment).
            if (!extension.isActive) {
                handleProgressMessage({
                    kind: 'begin',
                    id: 'activate-vscode-python',
                    title: 'Waiting for vscode-python activation...'
                });
                try {
                    await extension.activate();
                } finally {
                    handleProgressMessage({
                        kind: 'end',
                        id: 'activate-vscode-python',
                    });
                }

            }
            let execCommand = extension.exports.settings.getExecutionDetails(resource).execCommand;
            OUTPUT_CHANNEL.appendLine('vscode-python execution details: ' + execCommand);
            if (!execCommand) {
                OUTPUT_CHANNEL.appendLine('vscode-python did not return proper execution details.');
                return undefined;
            }
            // It could be some composite command such as conda activate, but that's ok, we don't want to consider those
            // a match for our use-case.
            return execCommand[0];
        } else {
            // Not using new interpreter storage (so, it should be queried from the settings).
            return 'config';
        }
    } catch (error) {
        OUTPUT_CHANNEL.appendLine('Error when querying about python executable path from vscode-python: ' + error);
        return undefined;
    }
}
