import * as monaco from 'monaco-editor';

interface IVSCode {
    postMessage(message: any): void;
}

declare const vscode: IVSCode;

// Note how request/response/event follows the same patterns from the 
// DAP (debug adapter protocol).
export interface IRequestMessage {
    type: 'request'
    seq: number
    command: string
}

export interface IResponseMessage {
    type: 'response'
    seq: number
    command: string
    request_seq: number
    body?: any
}

export interface IEventMessage {
    type: 'event'
    seq: number
    event: string
}

export interface IOutputEvent extends IEventMessage {
    category: string
    output: string
}

export interface IEvaluateMessage extends IRequestMessage {
    arguments: any
}

let msgIdToSeq = {};

export function sendRequestToClient(message: IRequestMessage): Promise<any> {
    let vscodeRef = undefined;
    try {
        vscodeRef = vscode;
    } catch (err) {
        // ignore
    }

    if (vscodeRef) {
        let promise = new Promise((resolve, reject) => {
            msgIdToSeq[message.seq] = resolve;
        })
        vscodeRef.postMessage(message);
        return promise;
    } else {
        // Unable to send to VSCode because we're not really connected
        // (case when html is opened directly and not through VSCode).
        return new Promise((resolve, reject) => {
            let response: IResponseMessage = {
                type: 'response',
                seq: nextMessageSeq(),
                command: message.command,
                request_seq: message.seq,
                body: undefined
            }
            resolve(response);
        });
    }
}


export function sendEventToClient(message: IEventMessage): void {
    let vscodeRef = undefined;
    try {
        vscodeRef = vscode;
    } catch (err) {
        // ignore
    }

    if (vscodeRef) {
        vscodeRef.postMessage(message);
    }
}

export let eventToHandler = {
    'output': undefined
}

export let requestToHandler = {
    'evaluate': undefined
}

// i.e.: Receive message from client
window.addEventListener('message', event => {
    let msg = event.data;
    if (msg) {
        switch (msg.type) {
            case 'response':
                // Response to something we posted.
                let responseMsg: IResponseMessage = msg;
                let resolvePromise = msgIdToSeq[responseMsg.request_seq];
                if (resolvePromise) {
                    delete msgIdToSeq[responseMsg.request_seq];
                    resolvePromise(responseMsg);
                }
                break;
            case 'event':
                // Process some event
                let handler = eventToHandler[msg.event];
                if (handler) {
                    handler(msg);
                } else {
                    console.log('Unhandled event: ', msg);
                }
                break;
            case 'request':
                // Process some request
                let requestHandler = requestToHandler[msg.command];
                if (requestHandler) {
                    requestHandler(msg);
                } else {
                    console.log('Unhandled request: ', msg);
                }
                break;
        }
    }
})


let _lastMessageId: number = 0;
export function nextMessageSeq(): number {
    _lastMessageId += 1;
    return _lastMessageId;
}
