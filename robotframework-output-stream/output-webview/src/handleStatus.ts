import { IContentAdded, IOpts } from "./protocols";

export function addStatus(current: IContentAdded, status: string) {
    const span = document.createElement("span");
    span.textContent = status;
    span.classList.add("label");
    span.classList.add(status.replace(" ", "_"));
    current.summaryDiv.insertBefore(span, current.summaryDiv.firstChild);
}

export function addTime(current: IContentAdded, diff: number) {
    const span = document.createElement("span");
    span.textContent = ` (${diff.toFixed(2)}s)`;
    span.classList.add("timeLabel");
    current.summaryDiv.appendChild(span);
}

export function acceptLevel(opts: IOpts, statusLevel: number) {
    switch (opts.state.filterLevel) {
        case "FAIL":
            return statusLevel >= 2;
        case "WARN":
            return statusLevel >= 1;
        case "PASS":
            return true;
    }
}

export function getIntLevelFromStatus(status: string): number {
    switch (status) {
        case "FAIL":
        case "ERROR":
            return 2;
        case "WARN":
            return 1;
        default:
            return 0;
    }
}
