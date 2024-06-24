import { commands, window } from "vscode";
import { getIntegrationToUse } from "./robocorpOrSema4ai";

export const OUTPUT_CHANNEL_NAME = "Robot Framework";
export const OUTPUT_CHANNEL = window.createOutputChannel(OUTPUT_CHANNEL_NAME);

export async function errorFeedback(errorCode: string) {
    try {
        const integration = getIntegrationToUse();
        if (integration !== "none") {
            await commands.executeCommand(`${integration}.errorFeedback.internal`, "vscode.lsp.error", errorCode);
        }
    } catch (err) {
        // that's ok, it may not be there.
    }
}

export async function feedback(name: string, value: string) {
    try {
        const integration = getIntegrationToUse();
        if (integration !== "none") {
            await commands.executeCommand(`${integration}.feedback.internal`, name, value);
        }
    } catch (err) {
        // that's ok, it may not be there.
    }
}

export function logError(msg: string, err: Error, errorCode: string | undefined) {
    if (errorCode !== undefined) {
        errorFeedback(errorCode);
    }
    OUTPUT_CHANNEL.appendLine(msg);
    let indent = "    ";
    if (err.message) {
        OUTPUT_CHANNEL.appendLine(indent + err.message);
    }
    if (err.stack) {
        let stack: string = "" + err.stack;
        OUTPUT_CHANNEL.appendLine(stack.replace(/^/gm, indent));
    }
}
