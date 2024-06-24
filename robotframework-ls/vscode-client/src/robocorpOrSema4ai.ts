import { extensions } from "vscode";
import { OUTPUT_CHANNEL } from "./channel";

let useIntegration: "robocorp" | "sema4ai" | "none" | undefined = undefined;

export const getIntegrationToUse = (): "robocorp" | "sema4ai" | "none" => {
    if (useIntegration) {
        return useIntegration;
    }
    const robocorpExt = extensions.getExtension("robocorp.robocorp-code");
    const sema4aiExt = extensions.getExtension("sema4ai.sema4ai");
    if (sema4aiExt) {
        OUTPUT_CHANNEL.appendLine("Using integration with Sema4.ai VSCoode Extension.");
        useIntegration = "sema4ai";
        return useIntegration;
    }

    if (robocorpExt) {
        OUTPUT_CHANNEL.appendLine("Using integration with Robocorp Code Extension.");
        useIntegration = "robocorp";
        return useIntegration;
    }

    OUTPUT_CHANNEL.appendLine("NOT using integration with Robocorp Code nor Sema4ai.");
    useIntegration = "none";
    return useIntegration;
};
