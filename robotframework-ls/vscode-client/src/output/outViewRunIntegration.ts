/**
 * This module provides the integration for providing contents to the output view.
 *
 * There are 2 sources of information to the output view:
 *
 * 1. Files in the filesystem:
 *      In this case, whenever the user selects a file which can have output
 *      information we should register the file and provide its content.
 *      Note that if the file is changed while tracking it we should notify
 *      the view accordingly.
 *
 * 2. Runs in memory:
 *      In this case, the idea is that when a run is done we can start collecting
 *      its information so that we can show what's happening with it.
 *
 * Also, note that the idea is that the output view acts only on 1 run, so,
 * all the state management related to keeping the state of a run must be
 * done in the extension side.
 */
import * as vscode from "vscode";
import { OUTPUT_CHANNEL } from "../channel";

class OutputViewState {
    storageUri: vscode.Uri | undefined = undefined;
    workspaceState: vscode.Memento | undefined = undefined;

    runIds: string[] = [];

    constructor(storageUri: vscode.Uri | undefined, workspaceState: vscode.Memento | undefined) {
        this.storageUri = storageUri;
        this.workspaceState = workspaceState;
    }

    /**
     * @param runId the run id which should be tracked
     */
    public async addRun(runId: string) {}

    public async setRunContents(runId: string, contents: string) {}

    public async appendToRunContents(runId: string, contents: string) {}
}

let globalOutputViewState: OutputViewState;

function isRelatedSession(session: vscode.DebugSession) {
    return session.configuration.type === "robotframework-lsp" && session.configuration.runId !== undefined;
}

export async function setupDebugSessionOutViewIntegration(context: vscode.ExtensionContext) {
    globalOutputViewState = new OutputViewState(context.storageUri, context.workspaceState);

    vscode.debug.onDidStartDebugSession((session: vscode.DebugSession) => {
        if (isRelatedSession(session)) {
            globalOutputViewState.addRun(session.configuration.runId);
        }
    });

    vscode.debug.onDidTerminateDebugSession((session: vscode.DebugSession) => {
    });

    vscode.debug.onDidReceiveDebugSessionCustomEvent((event: vscode.DebugSessionCustomEvent) => {
        if (isRelatedSession(event.session)) {
            // OUTPUT_CHANNEL.appendLine("Received event: " + event.event + " -- " + JSON.stringify(event.body));
            const runId = event.session.configuration.runId;
        }
    });
}
