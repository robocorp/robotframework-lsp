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

class Contents {
    public runId: string;
    public label: string;
    private contents: string[];

    constructor(runId: string, label: string, contents: string) {
        this.runId = runId;
        this.label = label;
        this.contents = [contents];
    }

    getFullContents() {
        return this.contents.join("");
    }

    addContent(line: string) {
        this.contents.push(line);
    }
}

interface ISetContentsRequest {
    type: "request";
    command: "setContents";
    initialContents: string;
    runId: string;
    allRunIdsToLabel: object;
}

interface IAppendContentsRequest {
    type: "request";
    command: "appendContents";
    appendContents: string;
    runId: string;
}

interface IUpdateLabelRequest {
    type: "request";
    command: "updateLabel";
    runId: string;
    label: string;
}

class OutputViewState {
    storageUri: vscode.Uri | undefined = undefined;

    workspaceState: vscode.Memento | undefined = undefined;

    currentRunId: string | undefined;

    // NOTE: runIds is a FIFO
    runIds: string[] = [];

    runIdToContents: Map<string, Contents> = new Map();

    webview: vscode.Webview | undefined;

    constructor(storageUri: vscode.Uri | undefined, workspaceState: vscode.Memento | undefined) {
        this.storageUri = storageUri;
        this.workspaceState = workspaceState;
    }

    async setWebview(webview: vscode.Webview | undefined) {
        this.webview = webview;
    }

    updateAfterVisible() {
        if (this.currentRunId !== undefined) {
            this.setCurrentRunId(this.currentRunId);
        }
    }

    async setCurrentRunId(runId: string) {
        this.currentRunId = runId;
        const webview = this.webview;
        if (webview !== undefined) {
            const contents = this.runIdToContents.get(runId);
            if (contents === undefined) {
                OUTPUT_CHANNEL.appendLine("No contents registered for runId: " + runId);
                return;
            }
            const allRunIdsToLabel: object = {};
            for (const rId of this.runIds) {
                const c = this.runIdToContents.get(rId);
                if (c !== undefined) {
                    allRunIdsToLabel[rId] = c.label;
                }
            }
            const msg: ISetContentsRequest = {
                type: "request",
                command: "setContents",
                "initialContents": contents.getFullContents(),
                "runId": runId,
                "allRunIdsToLabel": allRunIdsToLabel,
            };
            webview.postMessage(msg);
        }
    }

    /**
     * @param runId the run id which should be tracked.
     */
    public async addRun(runId: string, label: string, contents: string) {
        this.runIds.push(runId);
        const MAX_RUNS_SHOWN = 15;
        while (this.runIds.length > MAX_RUNS_SHOWN) {
            // NOTE: runIds is a FIFO
            let removeI = 0;
            let removeRunId = this.runIds[removeI];
            this.runIdToContents.delete(removeRunId);
            this.runIds.splice(removeI, 1);
        }

        this.runIdToContents.set(runId, new Contents(runId, label, contents));
        await this.setCurrentRunId(runId);
    }

    public async setRunLabel(runId: string, label: string) {
        const contents = this.runIdToContents.get(runId);
        if (contents !== undefined) {
            contents.label = label;

            const webview = this.webview;
            if (webview !== undefined) {
                const msg: IUpdateLabelRequest = {
                    type: "request",
                    command: "updateLabel",
                    "runId": runId,
                    "label": label,
                };
                webview.postMessage(msg);
            }
        }
    }

    public async appendToRunContents(runId: string, line: string) {
        const runContents = this.runIdToContents.get(runId);
        if (runContents !== undefined) {
            runContents.addContent(line);
        }
        if (runId === this.currentRunId) {
            const webview = this.webview;
            if (webview !== undefined) {
                const msg: IAppendContentsRequest = {
                    type: "request",
                    command: "appendContents",
                    "appendContents": line,
                    "runId": runId,
                };
                webview.postMessage(msg);
            }
        }
    }
}

export let globalOutputViewState: OutputViewState;

function isRelatedSession(session: vscode.DebugSession) {
    return session.configuration.type === "robotframework-lsp" && session.configuration.runId !== undefined;
}

/**
 * Must provide a unique id that is different even across restarts.
 */
function getUniqueId(session: vscode.DebugSession) {
    return session.id + session.configuration.runId;
}

export async function setupDebugSessionOutViewIntegration(context: vscode.ExtensionContext) {
    globalOutputViewState = new OutputViewState(context.storageUri, context.workspaceState);

    vscode.debug.onDidStartDebugSession((session: vscode.DebugSession) => {
        if (isRelatedSession(session)) {
            globalOutputViewState.addRun(getUniqueId(session), session.configuration.runId, "");
        }
    });

    vscode.debug.onDidTerminateDebugSession((session: vscode.DebugSession) => {
        if (isRelatedSession(session)) {
            globalOutputViewState.setRunLabel(getUniqueId(session), session.configuration.runId + " (finished)");
        }
    });

    vscode.debug.onDidReceiveDebugSessionCustomEvent((event: vscode.DebugSessionCustomEvent) => {
        if (isRelatedSession(event.session)) {
            if (event.event === "rfStream") {
                // OUTPUT_CHANNEL.appendLine("Received event: " + event.event + " -- " + JSON.stringify(event.body));
                const runId = getUniqueId(event.session);
                const msg = event.body["msg"];
                globalOutputViewState.appendToRunContents(runId, msg);
            }
        }
    });
}
