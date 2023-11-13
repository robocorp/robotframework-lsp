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
    LOCATORS_MANAGER = "locatorsManager",
    WEB_RECORDER = "webRecorder",
    WINDOWS_RECORDER = "windowsRecorder",
}

export type IAppsType = IApps.LOCATORS_MANAGER | IApps.WEB_RECORDER | IApps.WINDOWS_RECORDER;

// =====================================
// REQUESTS
// =====================================
export type IManagerCommands = { type: "getLocators" } | { type: "delete"; ids: string[] };
export type IWebRecorderCommands =
    | { type: "getLocators" }
    | { type: "startPicking" }
    | { type: "stopPicking" }
    | { type: "delete"; ids: string[] }
    | { type: "save"; locator: Locator }
    | { type: "validate"; locator: Locator };

export type IWindowsRecorderCommands =
    | { type: "getLocators" }
    | { type: "getAppWindows" }
    | { type: "setSelectedApp"; handle: string }
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
    command: IManagerCommands | IWebRecorderCommands | IWindowsRecorderCommands;
}

// =====================================
// RESPONSES
// =====================================
export type ResponseDataType = "locator" | "locatorsMap" | "winApps";
export type WindowsApplicationsResponse = { executable: string; name: string; handle: string }[];

// IResponseMessage - should respond to a Request
export interface IResponseMessage {
    id: number;
    type: IMessageType.RESPONSE;
    app: IAppsType;
    status: "success" | "failure";
    message?: string;
    data?: Locator | LocatorsMap | WindowsApplicationsResponse;
    dataType?: ResponseDataType;
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
