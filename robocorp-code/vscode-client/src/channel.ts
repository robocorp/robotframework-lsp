import { window } from "vscode";
import { feedbackRobocorpCodeError } from "./rcc";

export const OUTPUT_CHANNEL_NAME = "Robocorp Code";
export const OUTPUT_CHANNEL = window.createOutputChannel(OUTPUT_CHANNEL_NAME);

export function buildErrorStr(err: Error | undefined) {
    let ret = "";
    if (err !== undefined) {
        let indent = "    ";
        if (err.message) {
            ret += indent + err.message;
        }
        if (err.stack) {
            let stack: string = "" + err.stack;
            ret += stack.replace(/^/gm, indent);
        }
    } else {
        ret = "<Error is undefined>";
    }
    return ret;
}

export function showErrorAndStackOnOutput(err: Error | undefined) {
    if (err !== undefined) {
        let indent = "    ";
        if (err.message) {
            OUTPUT_CHANNEL.appendLine(indent + err.message);
        }
        if (err.stack) {
            let stack: string = "" + err.stack;
            OUTPUT_CHANNEL.appendLine(stack.replace(/^/gm, indent));
        }
    }
}

export function logError(msg: string, err: Error | undefined, errorCode: string) {
    feedbackRobocorpCodeError(errorCode); // async, but don't wait for it

    OUTPUT_CHANNEL.appendLine(msg);
    showErrorAndStackOnOutput(err);
}
