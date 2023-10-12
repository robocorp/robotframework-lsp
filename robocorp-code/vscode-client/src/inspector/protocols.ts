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

export type IManagerCommands = { type: "delete"; name: string } | { type: "rename"; name: string };
export type IWebPickerCommands =
    | { type: "startPicking" }
    | { type: "stopPicking" }
    | { type: "delete"; ids: string[] }
    | { type: "save"; locator: Locator }
    | { type: "validate"; locator: Locator };

export interface IRequestMessage {
    id: number;
    type: IMessageType.REQUEST;
    app: IAppsType;
    command: IManagerCommands | IWebPickerCommands;
}

export type IManagerData = { type: "locators"; data: LocatorsMap };
export type IWebPickerData = { type: "locator"; data: Locator };

export interface IResponseMessage {
    id: number;
    type: IMessageType.RESPONSE;
    app: IAppsType;
    data?: IManagerData | IWebPickerData;
}

export interface IEventMessage {
    id: number;
    type: IMessageType.EVENT;
    event: { type: "locatorsUpdate"; data: LocatorsMap };
}

export type IMessage = IRequestMessage | IResponseMessage | IEventMessage;
