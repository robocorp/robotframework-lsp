import { IMessage } from "./decoder";

export interface ITreeState {
    openNodes: object;
}

type IRunIdToTreeState = {
    [key: string]: ITreeState;
};

export interface IState {
    filterLevel: IFilterLevel;
    runIdToTreeState: IRunIdToTreeState;
    runIdLRU: string[];
}

export type IFilterLevel = "FAIL" | "WARN" | "PASS";

export interface IOpts {
    runId: string;
    state: IState | undefined;
    onClickReference: Function | undefined;
    allRunIdsToLabel: object;

    // Contains the initial file contents.
    initialContents: string;

    // Contains the contents added afterwards (i.e.:
    // we may add the contents for a session up to a point
    // and then add new messages line by line as it's
    // being tracked afterwards).
    appendedContents: string[];
}

export interface IContentAdded {
    ul: HTMLUListElement;
    li: HTMLLIElement;
    details: HTMLDetailsElement;
    summary: HTMLElement;
    summaryDiv: HTMLDivElement;
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

export interface IMessageNode {
    message: IMessage;
    parent: IMessageNode;
}
