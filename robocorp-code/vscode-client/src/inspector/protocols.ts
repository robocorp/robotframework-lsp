/**
 * @source https://github.com/robocorp/inspector-ext/blob/master/src/vscode/protocols.ts
 *! THIS FILE NEEDS TO ALWAYS MATCH THE SOURCE
 */

import { Locator, LocatorsMap } from "./types";

export enum IMessageType {
    REQUEST = "request",
    RESPONSE = "response",
    EVENT = "event",
}

export enum IApps {
    LOCATOR_MANAGER = "locatorManager",
    WEB_PICKER = "webPicker",
}

export type IAppsType = IApps.LOCATOR_MANAGER | IApps.WEB_PICKER;
// =====================================
// REQUESTS
// =====================================
export type IManagerCommands = { type: "getLocators" } | { type: "delete"; name: string };
export type IWebPickerCommands =
    | { type: "getLocators" }
    | { type: "startPicking" }
    | { type: "stopPicking" }
    | { type: "delete"; ids: string[] }
    | { type: "save"; locator: Locator }
    | { type: "validate"; locator: Locator };

// IResponseMessage - should be sent with an expectation of Response
export interface IRequestMessage {
    id: number;
    type: IMessageType.REQUEST;
    app: IAppsType;
    command: IManagerCommands | IWebPickerCommands;
}

// =====================================
// RESPONSES
// =====================================
// IResponseMessage - should respond to a Request
export interface IResponseMessage {
    id: number;
    type: IMessageType.RESPONSE;
    app: IAppsType;
    status: "success" | "failure";
    message?: string;
    data?: Locator | LocatorsMap;
    dataType?: "locator" | "locatorsMap";
}

// IResponseMessage - should be equidistant from Requests or Responses
export interface IEventMessage {
    id: number;
    type: IMessageType.EVENT;
    event: {
        type: "pickedLocator";
        status: "success" | "failure";
        message?: string;
        data: Locator;
    };
}
export type IMessage = IRequestMessage | IResponseMessage | IEventMessage;
