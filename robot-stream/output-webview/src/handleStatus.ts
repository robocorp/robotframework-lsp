import { IOpts } from "./protocols";

export function addStatus(summary: HTMLElement, status: string) {
    const span = document.createElement("span");
    span.textContent = status;
    span.classList.add("label");
    span.classList.add(status.replace(" ", "_"));
    summary.insertBefore(span, summary.firstChild);
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
