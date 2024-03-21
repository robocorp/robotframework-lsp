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
    JAVA_INSPECTOR = "javaInspector",
}

export type IAppsType =
    | IApps.LOCATORS_MANAGER
    | IApps.WEB_INSPECTOR
    | IApps.WINDOWS_INSPECTOR
    | IApps.IMAGE_INSPECTOR
    | IApps.JAVA_INSPECTOR;

export enum IAppRoutes {
    LOCATORS_MANAGER = "/locators-manager/",
    WEB_INSPECTOR = "/web-inspector/",
    WINDOWS_INSPECTOR = "/windows-inspector/",
    IMAGE_INSPECTOR = "/image-inspector/",
    JAVA_INSPECTOR = "/java-inspector/",
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
    | { type: "startPicking"; url?: string; viewportWidth?: number; viewportHeight?: number }
    | { type: "stopPicking" }
    | { type: "validate"; locator: Locator; url?: string }
    | { type: "killMe" };

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
    | { type: "validate"; locator: Locator }
    | { type: "killMe" };

export type IImageInspectorCommands =
    | { type: "startPicking"; minimize?: boolean; confidenceLevel?: number }
    | { type: "stopPicking" }
    | { type: "validate"; locator: Locator }
    | { type: "saveImage"; imageBase64: string }
    | { type: "killMe" };

export type IJavaInspectorCommands =
    | { type: "getLocators" }
    | { type: "getAppJava" }
    | { type: "collectAppTree"; locator: string; depth?: number }
    | { type: "setSelectedApp"; handle: string }
    | { type: "validateLocatorSyntax"; locator: string }
    | { type: "startPicking" }
    | { type: "stopPicking" }
    | { type: "startHighlighting"; locator: string; depth?: number }
    | { type: "stopHighlighting" }
    | { type: "validate"; locator: Locator }
    | { type: "killMe" };

// IResponseMessage - should be sent with an expectation of Response
export interface IRequestMessage {
    id: string;
    type: IMessageType.REQUEST;
    app: IAppsType;
    command:
        | IManagerCommands
        | IWebInspectorCommands
        | IWindowsInspectorCommands
        | IImageInspectorCommands
        | IJavaInspectorCommands;
}

// =====================================
// RESPONSES
// =====================================
// == WINDOWS
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

// == IMAGE
export type ImagePickResponse = {
    screenshot: string;
    screenResolutionWidth: number;
    screenResolutionHeight: number;
    screenPixelRatio: number;
    matches: number;
    confidence: number;
};

// == Java
export type JavaAppDetails = { pid: number; hwnd: number; title: string };
export type JavaAppsResponse = JavaAppDetails[];
export type JavaAppElement = {
    name: string;
    role: string;
    description: string;
    states: string[];
    statesString: string;
    checked: boolean;
    selected: boolean;
    visible: boolean;
    showing: boolean;
    focusable: boolean;
    enabled: boolean;
    x: number;
    y: number;
    width: number;
    height: number;
    row: number;
    col: number;
    indexInParent: number;
    childrenCount: number;
    text: string;
    ancestry: number;
};
export type JavaAppTree = JavaAppElement[];
export type JavaAppTreeResponse = {
    matched_paths: string[];
    hierarchy: JavaAppTree;
};

// == INTERFACE
export type ResponseDataType =
    | "locator"
    | "locatorsMap"
    | "winApps"
    | "winAppTree"
    | "locatorMatches"
    | "imagePath"
    | "javaApps"
    | "javaAppTree";
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
        | {
              type: "locatorMatches";
              value: number;
          }
        | { type: "winApps"; value: WindowsAppsResponse }
        | {
              type: "winAppTree";
              value: WindowsAppTreeResponse;
          }
        | {
              type: "imagePath";
              value: string;
          }
        | { type: "javaApps"; value: JavaAppsResponse }
        | {
              type: "javaAppTree";
              value: JavaAppTreeResponse;
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
    event: // generics
    | {
              type: "gotoInspectorApp";
              status: SuccessORFailure;
              message?: string;
              data: IAppRoutes;
          }
        | {
              type: "pickedLocator";
              status: SuccessORFailure;
              message?: string;
              data: Locator;
          }
        // web
        | {
              type: "browserState";
              status: SuccessORFailure;
              message?: string;
              data: ReportedStates;
          }
        | {
              type: "urlChange";
              status: SuccessORFailure;
              message?: string;
              data: string;
          }
        // windows
        | {
              type: "pickedWinLocatorTree";
              status: SuccessORFailure;
              message?: string;
              data: WindowsAppTree;
          }
        // image
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
          }
        // java
        | {
              type: "pickedJavaLocatorTree";
              status: SuccessORFailure;
              message?: string;
              data: JavaAppTree;
          };
}
export type IMessage = IRequestMessage | IResponseMessage | IEventMessage;
