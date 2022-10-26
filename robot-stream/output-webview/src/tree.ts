// Interesting reads:
// https://medium.com/metaphorical-web/javascript-treeview-controls-devil-in-the-details-74c252e00ed8
// https://iamkate.com/code/tree-views/
// https://stackoverflow.com/questions/10813581/can-i-replace-the-expand-icon-of-the-details-element

import { IMessage } from "./decoder";
import { IContentAdded, IOpts } from "./protocols";

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
    lineno: number
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

    const li: HTMLLIElement = document.createElement("li");
    const details: HTMLDetailsElement = document.createElement("details");
    details.open = open;
    const summary = document.createElement("summary");

    li.appendChild(details);
    details.appendChild(summary);
    details.classList.add("NO_CHILDREN");

    const span: HTMLSpanElement = document.createElement("span");
    span.setAttribute("role", "button");
    span.textContent = content;
    summary.appendChild(span);

    if (opts.onClickReference) {
        span.classList.add("span_link");
        span.onclick = (ev) => {
            ev.preventDefault();
            opts.onClickReference({
                source,
                lineno,
                "message": decodedMessage.decoded,
                "messageType": decodedMessage.message_type,
            });
        };
    }

    const ul = document.createElement("ul");
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
