import { IMessage } from "./decoder";

export interface IState {
    filterLevel: IFilterLevel;
}

export type IFilterLevel = "FAIL" | "WARN" | "PASS";

export interface IOpts {
    outputFileContents: string;
    runId: string;
    state: IState | undefined;
    viewMode: "hierarchy" | "flat";
    onClickReference: Function | undefined;
}

export interface IContentAdded {
    ul: HTMLElement;
    li: HTMLElement;
    details: HTMLElement;
    summary: HTMLElement;
    span: HTMLElement;
    source: string;
    lineno: number;

    appendContentChild: any;
    decodedMessage: IMessage;

    // Updated when the status or level for an element is set (usually at the end).
    // When a given item finishes updating it'll update its parent accordingly.
    // 0 = pass, 1= warn, 2=error
    maxLevelFoundInHierarchy: number;
}
