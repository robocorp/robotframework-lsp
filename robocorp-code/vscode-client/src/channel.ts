import { window } from "vscode";
import { feedbackRobocorpCodeError } from "./rcc";

export const OUTPUT_CHANNEL_NAME = "Robocorp Code";
export const OUTPUT_CHANNEL = window.createOutputChannel(OUTPUT_CHANNEL_NAME);

export function logError(msg: string, err: Error, errorCode: string) {
    feedbackRobocorpCodeError(errorCode);

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
