// Interesting reads:
// https://medium.com/metaphorical-web/javascript-treeview-controls-devil-in-the-details-74c252e00ed8
// https://iamkate.com/code/tree-views/
// https://stackoverflow.com/questions/10813581/can-i-replace-the-expand-icon-of-the-details-element

import { IMessage } from "./decoder";
import { createDetails, createLI, createSpan, createSummary, createUL, getDataTreeId } from "./plainDom";
import { IContentAdded, IMessageNode, IOpts, ITreeState } from "./protocols";

/**
 * When we add content we initially add it as an item with the NO_CHILDREN class
 * and later we have to remove that class if it has children.
 */
export function addTreeContent(
    opts: IOpts,
    parent: IContentAdded,
    content: string,
    decodedMessage: IMessage,
    open: boolean,
    source: string,
    lineno: number,
    messageNode: IMessageNode,
    id: string
): IContentAdded {
    // <li>
    //   <details open>
    //     <summary>
    //          <span></span>
    //     </summary>
    //     <ul>
    //     </ul>
    //   </details>
    // </li>

    const treeState: ITreeState = opts.state.runIdToTreeState[opts.runId];
    let openNodes = {};
    if (treeState) {
        openNodes = treeState.openNodes;
    }

    const liTreeId = "li_" + id;
    const li: HTMLLIElement = createLI(liTreeId);

    const details: HTMLDetailsElement = createDetails();
    if (open) {
        details.open = open;
    } else {
        if (openNodes[liTreeId]) {
            details.open = true;
        }
    }
    const summary = createSummary();

    li.appendChild(details);
    details.appendChild(summary);
    details.classList.add("NO_CHILDREN");

    const span: HTMLSpanElement = createSpan();
    span.setAttribute("role", "button");
    span.textContent = content;
    summary.appendChild(span);

    if (opts.onClickReference) {
        span.classList.add("span_link");
        span.onclick = (ev) => {
            const scope = [];
            let p: IMessageNode = messageNode.parent;
            while (p !== undefined && p.message !== undefined) {
                scope.push(p.message);
                p = p.parent;
            }

            ev.preventDefault();
            opts.onClickReference({
                source,
                lineno,
                "message": decodedMessage.decoded,
                "messageType": decodedMessage.message_type,
                "scope": scope,
            });
        };
    }

    const ul = createUL("ul_" + id);
    details.appendChild(ul);
    const ret = {
        ul,
        li,
        details,
        summary,
        span,
        source,
        lineno,
        appendContentChild: undefined,
        decodedMessage,
        maxLevelFoundInHierarchy: 0,
    };
    ret["appendContentChild"] = createUlIfNeededAndAppendChild.bind(ret);
    parent.appendContentChild(ret);
    return ret;
}

function createUlIfNeededAndAppendChild(child: IContentAdded) {
    this.ul.appendChild(child.li);
    this.details.classList.remove("NO_CHILDREN");
    //     if (this.ul === undefined) {
    //         this.li.appendChild(this.details);
    //         this.details.appendChild(this.summary);
    //         const ul = document.createElement("ul");
    //         this.details.appendChild(ul);
    //         this.ul = ul;
    //     }
    //     this.ul.appendChild(child);
}

function collectLITreeState(state: ITreeState, li: HTMLLIElement) {
    for (let child of li.childNodes) {
        if (child instanceof HTMLDetailsElement) {
            for (let c of child.childNodes) {
                if (c instanceof HTMLUListElement) {
                    collectUlTreeState(state, c);
                }
            }
            if (child.open) {
                state.openNodes[getDataTreeId(li)] = "open";
            } else {
                delete state.openNodes[getDataTreeId(li)];
            }
        }
    }
}

export function collectUlTreeState(state: ITreeState, ul: HTMLUListElement) {
    for (let child of ul.childNodes) {
        if (child instanceof HTMLLIElement) {
            collectLITreeState(state, child);
        }
    }
}
