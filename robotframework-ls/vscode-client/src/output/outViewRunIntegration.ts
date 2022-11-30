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
import { nextRunId } from "../testview";

class Contents {
    public uniqueRunId: string;
    public label: string;
    private contents: string[];

    constructor(uniqueRunId: string, label: string, contents: string) {
        this.uniqueRunId = uniqueRunId;
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

    currentRunUniqueId: string | undefined;

    // NOTE: uniqueRunIds is a FIFO
    uniqueRunIds: string[] = [];

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
        if (this.currentRunUniqueId !== undefined) {
            this.setCurrentRunId(this.currentRunUniqueId);
        }
    }

    async setCurrentRunId(uniqueRunId: string) {
        this.currentRunUniqueId = uniqueRunId;
        const webview = this.webview;
        if (webview !== undefined) {
            const contents = this.runIdToContents.get(uniqueRunId);
            if (contents === undefined) {
                OUTPUT_CHANNEL.appendLine("No contents registered for runId: " + uniqueRunId);
                return;
            }
            const allRunIdsToLabel: object = {};
            for (const rId of this.uniqueRunIds) {
                const c = this.runIdToContents.get(rId);
                if (c !== undefined) {
                    allRunIdsToLabel[rId] = c.label;
                }
            }
            const msg: ISetContentsRequest = {
                type: "request",
                command: "setContents",
                "initialContents": contents.getFullContents(),
                "runId": uniqueRunId,
                "allRunIdsToLabel": allRunIdsToLabel,
            };
            webview.postMessage(msg);
        }
    }

    /**
     * @param runId the run id which should be tracked.
     */
    public async addRun(uniqueRunId: string, label: string, contents: string) {
        this.uniqueRunIds.push(uniqueRunId);
        const MAX_RUNS_SHOWN = 15;
        while (this.uniqueRunIds.length > MAX_RUNS_SHOWN) {
            // NOTE: uniqueRunIds is a FIFO
            let removeI = 0;
            let removeRunId = this.uniqueRunIds[removeI];
            this.runIdToContents.delete(removeRunId);
            this.uniqueRunIds.splice(removeI, 1);
        }

        this.runIdToContents.set(uniqueRunId, new Contents(uniqueRunId, label, contents));
        await this.setCurrentRunId(uniqueRunId);
    }

    public async setRunLabel(uniqueRunId: string, label: string) {
        const contents = this.runIdToContents.get(uniqueRunId);
        if (contents !== undefined) {
            contents.label = label;

            const webview = this.webview;
            if (webview !== undefined) {
                const msg: IUpdateLabelRequest = {
                    type: "request",
                    command: "updateLabel",
                    "runId": uniqueRunId,
                    "label": label,
                };
                webview.postMessage(msg);
            }
        }
    }

    public async appendToRunContents(uniqueRunId: string, line: string) {
        const runContents = this.runIdToContents.get(uniqueRunId);
        if (runContents !== undefined) {
            runContents.addContent(line);
        }
        if (uniqueRunId === this.currentRunUniqueId) {
            const webview = this.webview;
            if (webview !== undefined) {
                const msg: IAppendContentsRequest = {
                    type: "request",
                    command: "appendContents",
                    "appendContents": line,
                    "runId": uniqueRunId,
                };
                webview.postMessage(msg);
            }
        }
    }
}

export let globalOutputViewState: OutputViewState;

function isRelatedSession(session: vscode.DebugSession) {
    return session.configuration.type === "robotframework-lsp";
}

/**
 * Must provide a unique id that is different even across restarts.
 */
function getUniqueId(session: vscode.DebugSession) {
    return session.id;
}

function getLabel(session: vscode.DebugSession): string {
    let label = session.configuration.runId;
    if (!label) {
        label = session.configuration.label;
        if (!label) {
            label = nextRunId();
            session.configuration.label = label;
        }
    }
    return label;
}

export async function setupDebugSessionOutViewIntegration(context: vscode.ExtensionContext) {
    globalOutputViewState = new OutputViewState(context.storageUri, context.workspaceState);

    vscode.debug.onDidStartDebugSession((session: vscode.DebugSession) => {
        if (isRelatedSession(session)) {
            const label = getLabel(session);
            globalOutputViewState.addRun(getUniqueId(session), label, "");
        }
    });

    vscode.debug.onDidTerminateDebugSession((session: vscode.DebugSession) => {
        if (isRelatedSession(session)) {
            const label = getLabel(session);
            globalOutputViewState.setRunLabel(getUniqueId(session), label + " (finished)");
        }
    });

    vscode.debug.onDidReceiveDebugSessionCustomEvent((event: vscode.DebugSessionCustomEvent) => {
        if (isRelatedSession(event.session)) {
            if (event.event === "rfStream") {
                // OUTPUT_CHANNEL.appendLine("Received event: " + event.event + " -- " + JSON.stringify(event.body));
                const uniqueRunId = getUniqueId(event.session);
                const msg = event.body["msg"];
                globalOutputViewState.appendToRunContents(uniqueRunId, msg);
            }
        }
    });
}
