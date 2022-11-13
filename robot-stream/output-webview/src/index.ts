import { getOpts } from "./options";
import { saveTreeState } from "./persistTree";
import { selectById } from "./plainDom";
import { IFilterLevel } from "./protocols";
import { getSampleContents } from "./sample";
import "./style.css";
import { TreeBuilder } from "./treeBuilder";
import {
    requestToHandler,
    sendEventToClient,
    nextMessageSeq,
    IEventMessage,
    ISetContentsRequest,
    IAppendContentsRequest,
} from "./vscodeComm";

let treeBuilder: TreeBuilder | undefined;

async function rebuildTreeAndStatusesFromOpts(): Promise<void> {
    treeBuilder = new TreeBuilder();
    treeBuilder.clearAndInitializeTree();
    await treeBuilder.addInitialContents();
}

export function updateFilterLevel(filterLevel: IFilterLevel) {
    const opts = getOpts();
    if (opts.state.filterLevel !== filterLevel) {
        opts.state.filterLevel = filterLevel;
        saveTreeState();
        rebuildTreeAndStatusesFromOpts();
    }
}

function onClickReference(message) {
    let ev: IEventMessage = {
        type: "event",
        seq: nextMessageSeq(),
        event: "onClickReference",
    };
    ev["data"] = message;
    sendEventToClient(ev);
}

/**
 * Should be called to set the initial contents of the tree
 * as well as the current run id and label.
 */
function setContents(msg: ISetContentsRequest): void {
    saveTreeState();
    const opts = getOpts();
    opts.runId = msg.runId;
    opts.initialContents = msg.initialContents;
    opts.onClickReference = onClickReference;
    opts.appendedContents = [];
    opts.label = msg.label;

    rebuildTreeAndStatusesFromOpts();
}

function appendContents(msg: IAppendContentsRequest): void {
    const opts = getOpts();
    if (opts.runId === msg.runId) {
        opts.appendedContents.push(msg.appendContents);
        if (treeBuilder !== undefined) {
            treeBuilder.onAppendedContents();
        }
    }
}

requestToHandler["setContents"] = setContents;
requestToHandler["appendContents"] = appendContents;

function onChangedFilterLevel() {
    const filterLevel = selectById("filterLevel");
    const value: IFilterLevel = <IFilterLevel>(<HTMLSelectElement>filterLevel).value;
    updateFilterLevel(value);
}

function onChangedRun() {}
window["onChangedRun"] = onChangedRun;
window["onChangedFilterLevel"] = onChangedFilterLevel;
window["setContents"] = setContents;
window["getSampleContents"] = getSampleContents;
