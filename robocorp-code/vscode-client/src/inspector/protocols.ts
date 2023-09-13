import { Locator, LocatorsMap } from "./types";

export type IApps = "locatorManager" | "webPicker";

export type IManagerCommands = { type: "delete"; name: string } | { type: "rename"; name: string };
export type IWebPickerCommands =
    | { type: "pick" }
    | { type: "save"; locator: Locator }
    | { type: "validate"; locator: Locator };

export interface IRequestMessage {
    type: "request";
    app: IApps;
    command: IManagerCommands | IWebPickerCommands;
}

export type IManagerData = { type: "locators"; data: LocatorsMap };
export type IWebPickerData = { type: "locator"; data: Locator };

export interface IResponseMessage {
    type: "response";
    app: IApps;
    data?: IManagerData | IWebPickerData;
}

export interface IEventMessage {
    type: "event";
    event: { type: "locatorsUpdate"; data: LocatorsMap };
}
