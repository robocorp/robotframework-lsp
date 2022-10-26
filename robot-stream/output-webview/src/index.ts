import { iter_decoded_log_format } from "./decoder";
import { addLevel, getIntLevelFromLevelStr } from "./handleLevel";
import { acceptLevel, addStatus, getIntLevelFromStatus } from "./handleStatus";
import { IContentAdded, IOpts } from "./protocols";
import { getSampleContents } from "./sample";
import "./style.css";
import { addTreeContent } from "./tree";
import { requestToHandler, sendEventToClient, nextMessageSeq, IEventMessage } from "./vscodeComm";

let lastOpts: IOpts | undefined = undefined;

export function updateFilterLevel(filterLevel: "FAIL" | "WARN" | "PASS") {
    if (!lastOpts) {
        return;
    }
    if (lastOpts.filterLevel !== filterLevel) {
        lastOpts.filterLevel = filterLevel;
        main(lastOpts);
    }
}

async function main(opts: IOpts) {
    lastOpts = opts;
    totalTests = 0;
    totalFailures = 0;
    updateSummary();

    const mainDiv: HTMLElement = document.getElementById("mainTree");
    mainDiv.replaceChildren(); // clear all children

    const rootUl = document.createElement("ul");
    rootUl.classList.add("tree");
    mainDiv.appendChild(rootUl);

    function addToRoot(el: IContentAdded) {
        rootUl.appendChild(el.li);
    }

    let parent: IContentAdded = {
        "ul": undefined,
        "li": undefined,
        "details": undefined,
        "summary": undefined,
        "span": undefined,
        "source": undefined,
        "lineno": undefined,
        "decodedMessage": undefined,
        "appendContentChild": addToRoot,
        "maxLevelFoundInHierarchy": 0,
    };
    const stack: IContentAdded[] = [];
    stack.push(parent);
    let suiteName = "";
    let suiteSource = "";
    for (const msg of iter_decoded_log_format(opts.outputFileContents)) {
        switch (msg.message_type) {
            case "SS":
                // start suite
                suiteName = msg.decoded["name"] + ".";
                suiteSource = msg.decoded["source"];
                // parent = addTreeContent(opts, parent, msg.decoded["name"], msg, true);
                // stack.push(parent);
                break;

            case "ST":
                // start test
                parent = addTreeContent(
                    opts,
                    parent,
                    suiteName + msg.decoded["name"],
                    msg,
                    false,
                    suiteSource,
                    msg.decoded["lineno"]
                );
                stack.push(parent);
                break;
            case "SK":
                // start keyword
                let libname = msg.decoded["libname"];
                if (libname) {
                    libname += ".";
                }
                parent = addTreeContent(
                    opts,
                    parent,
                    `${msg.decoded["keyword_type"]} - ${libname}${msg.decoded["name"]}`,
                    msg,
                    false,
                    msg.decoded["source"],
                    msg.decoded["lineno"]
                );
                stack.push(parent);
                break;
            case "ES": // end suite
                suiteName = "";
                break;
            case "ET": // end test
                const currT = parent;
                stack.pop();
                parent = stack.at(-1);
                onEndUpdateMaxLevelFoundInHierarchyFromStatus(currT, parent, msg);
                onEndSetStatusOrRemove(opts, currT, msg.decoded["status"]);
                onTestEndUpdateSummary(msg);
                break;
            case "EK": // end keyword
                let currK = parent;
                stack.pop();
                parent = stack.at(-1);
                onEndUpdateMaxLevelFoundInHierarchyFromStatus(currK, parent, msg);
                onEndSetStatusOrRemove(opts, currK, msg.decoded["status"]);
                break;
            case "KA":
                const item: IContentAdded = stack.at(-1);
                item.span.textContent += ` | ${msg.decoded}`;
                break;
            case "L":
                // A bit different because it's always leaf and based on 'level', not 'status'.
                const level = msg.decoded["level"];
                const iLevel = getIntLevelFromLevelStr(level);
                if (iLevel > parent.maxLevelFoundInHierarchy) {
                    parent.maxLevelFoundInHierarchy = iLevel;
                    console.log("set level", parent.decodedMessage, "to", iLevel);
                }
                if (acceptLevel(opts, iLevel)) {
                    const logContent = addTreeContent(
                        opts,
                        parent,
                        msg.decoded["message"],
                        msg,
                        false,
                        undefined,
                        undefined
                    );
                    logContent.maxLevelFoundInHierarchy = iLevel;
                    const summary = logContent.summary;
                    addLevel(summary, level);
                }

                break;
        }
    }

    return main;
}

let totalTests: number = 0;
let totalFailures: number = 0;
function onTestEndUpdateSummary(msg: any) {
    const status = msg.decoded["status"];
    totalTests += 1;
    if (status == "FAIL" || status == "ERROR") {
        totalFailures += 1;
    }
    updateSummary();
}

function updateSummary() {
    const totalTestsStr = ("" + totalTests).padStart(4);
    const totalFailuresStr = ("" + totalFailures).padStart(4);
    const summary: HTMLDivElement = <HTMLDivElement>document.getElementById("summary");
    summary.textContent = `Total: ${totalTestsStr} Failures: ${totalFailuresStr}`;

    if (totalFailures == 0 && totalTests == 0) {
        const resultBar: HTMLDivElement = <HTMLDivElement>document.getElementById("summary");
        resultBar.classList.add("NOT_RUN");
        resultBar.classList.remove("PASS");
        resultBar.classList.remove("FAIL");
    } else if (totalFailures == 1) {
        const resultBar: HTMLDivElement = <HTMLDivElement>document.getElementById("summary");
        resultBar.classList.remove("NOT_RUN");
        resultBar.classList.remove("PASS");
        resultBar.classList.add("FAIL");
    } else if (totalFailures == 0 && totalTests == 1) {
        const resultBar: HTMLDivElement = <HTMLDivElement>document.getElementById("summary");
        resultBar.classList.remove("NOT_RUN");
        resultBar.classList.remove("FAIL");
    }
}

function onEndUpdateMaxLevelFoundInHierarchyFromStatus(current: IContentAdded, parent: IContentAdded, msg: any) {
    const status = msg.decoded["status"];
    const iLevel = getIntLevelFromStatus(status);

    if (iLevel > current.maxLevelFoundInHierarchy) {
        current.maxLevelFoundInHierarchy = iLevel;
    }
    if (current.maxLevelFoundInHierarchy > parent.maxLevelFoundInHierarchy) {
        parent.maxLevelFoundInHierarchy = current.maxLevelFoundInHierarchy;
    }
}

function onEndSetStatusOrRemove(opts: IOpts, current: IContentAdded, status: string) {
    console.log("Level: ", current.maxLevelFoundInHierarchy, "for", current.decodedMessage);
    if (acceptLevel(opts, current.maxLevelFoundInHierarchy)) {
        const summary = current.summary;
        addStatus(summary, status);
    } else {
        current.li.remove();
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

function setContents(msg) {
    main({
        outputFileContents: msg.outputFileContents,
        filterLevel: "PASS",
        viewMode: "flat",
        onClickReference: onClickReference,
    });
}

requestToHandler["setContents"] = setContents;

function onChangedFilterLevel() {
    const filterLevel = document.getElementById("filterLevel");
    const value: "FAIL" | "WARN" | "PASS" = <"FAIL" | "WARN" | "PASS">(<HTMLSelectElement>filterLevel).value;
    updateFilterLevel(value);
}

function onChangedRun() {}
window["onChangedRun"] = onChangedRun;
window["onChangedFilterLevel"] = onChangedFilterLevel;
window["setContents"] = setContents;
window["getSampleContents"] = getSampleContents;
