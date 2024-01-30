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
    WEB_INSPECTOR = "webInspector",
    WINDOWS_INSPECTOR = "windowsInspector",
    IMAGE_INSPECTOR = "imageInspector",
}

export type IAppsType = IApps.LOCATORS_MANAGER | IApps.WEB_INSPECTOR | IApps.WINDOWS_INSPECTOR | IApps.IMAGE_INSPECTOR;

export enum IAppRoutes {
    LOCATORS_MANAGER = "/locators-manager/",
    WEB_INSPECTOR = "/web-inspector/",
    WINDOWS_INSPECTOR = "/windows-inspector/",
    JAVA_INSPECTOR = "/java-inspector/",
    IMAGE_INSPECTOR = "/image-inspector/",
}

// =====================================
// REQUESTS
// =====================================
export type IManagerCommands =
    | { type: "getLocators" }
    | { type: "delete"; ids: string[] }
    | { type: "save"; locator: Locator };

export type IWebInspectorCommands =
    | { type: "getLocators" }
    | { type: "startPicking"; url?: string }
    | { type: "stopPicking" }
    | { type: "validate"; locator: Locator; url?: string };

export type IWindowsInspectorCommands =
    | { type: "getLocators" }
    | { type: "getAppWindows" }
    | { type: "collectAppTree"; locator: string; depth?: number; strategy?: "all" | "siblings" }
    | { type: "setSelectedApp"; handle: string }
    | { type: "validateLocatorSyntax"; locator: string }
    | { type: "startPicking" }
    | { type: "stopPicking" }
    | { type: "startHighlighting"; locator: string; depth?: number; strategy?: "all" | "siblings" }
    | { type: "stopHighlighting" }
    | { type: "validate"; locator: Locator };

export type IImageInspectorCommands =
    | { type: "startPicking"; minimize?: boolean; confidenceLevel?: number }
    | { type: "stopPicking" }
    | { type: "validate"; locator: Locator }
    | { type: "saveImage"; imageBase64: string };

// IResponseMessage - should be sent with an expectation of Response
export interface IRequestMessage {
    id: string;
    type: IMessageType.REQUEST;
    app: IAppsType;
    command: IManagerCommands | IWebInspectorCommands | IWindowsInspectorCommands | IImageInspectorCommands;
}

// =====================================
// RESPONSES
// =====================================
export type WindowsAppDetails = { executable: string; name: string; handle: string };
export type WindowsAppsResponse = WindowsAppDetails[];
export type WindowsAppElement = {
    control: string;
    class: string;
    name: string;
    automation_id: string;
    handle: number;
    left: number;
    right: number;
    top: number;
    bottom: number;
    width: number;
    height: number;
    xcenter: number;
    ycenter: number;
    depth: number;
    child_pos: number;
    path: string;
};
export type WindowsAppTree = WindowsAppElement[];
export type WindowsAppTreeResponse = {
    matched_paths: string[];
    hierarchy: WindowsAppTree;
};

export type ImagePickResponse = {
    screenshot: string;
    screenResolutionWidth: number;
    screenResolutionHeight: number;
    screenPixelRatio: number;
    matches: number;
    confidence: number;
};

export type ResponseDataType = "locator" | "locatorsMap" | "winApps" | "winAppTree" | "locatorMatches" | "imagePath";
// IResponseMessage - should respond to a Request
export interface IResponseMessage {
    id: string;
    type: IMessageType.RESPONSE;
    app: IAppsType;
    status: "success" | "failure";
    message?: string;
    data?:
        | {
              type: "locator";
              value: Locator;
          }
        | {
              type: "locatorsMap";
              value: LocatorsMap;
          }
        | { type: "winApps"; value: WindowsAppsResponse }
        | {
              type: "winAppTree";
              value: WindowsAppTreeResponse;
          }
        | {
              type: "locatorMatches";
              value: number;
          }
        | {
              type: "imagePath";
              value: string;
          };
}

// =====================================
// EVENTS
// =====================================
export type SuccessORFailure = "success" | "failure";
export type ReportedStates = "initializing" | "opened" | "closed" | "picking" | "notPicking";

export interface IEventMessage {
    id: string;
    type: IMessageType.EVENT;
    event:
        | {
              type: "gotoInspectorApp";
              status: SuccessORFailure;
              message?: string;
              data: IAppRoutes;
          }
        | {
              type: "browserState";
              status: SuccessORFailure;
              message?: string;
              data: ReportedStates;
          }
        | {
              type: "pickedLocator";
              status: SuccessORFailure;
              message?: string;
              data: Locator;
          }
        | {
              type: "urlChange";
              status: SuccessORFailure;
              message?: string;
              data: string;
          }
        | {
              type: "pickedWinLocatorTree";
              status: SuccessORFailure;
              message?: string;
              data: WindowsAppTree;
          }
        | {
              type: "pickedImageSnapshot";
              status: SuccessORFailure;
              message?: string;
              data: ImagePickResponse;
          }
        | {
              type: "pickedImageValidation";
              status: SuccessORFailure;
              message?: string;
              data: number;
          }
        | {
              type: "snippingToolState";
              status: SuccessORFailure;
              message?: string;
              data: ReportedStates;
          };
}
export type IMessage = IRequestMessage | IResponseMessage | IEventMessage;
