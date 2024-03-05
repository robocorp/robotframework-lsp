// InspectorType - needs to respect the types from vscode-client/src/inspector/types.ts
export enum InspectorType {
    WebInspector = "browser",
    WindowsInspector = "windows",
    ImageInspector = "image",
    JavaInspector = "java",
    PlaywrightRecorder = "playwright-recorder",
}

export type InspectorTypes = `${InspectorType}`;

export const DEFAULT_INSPECTOR_VALUE = {
    "browser": false,
    "windows": false,
    "image": false,
    "java": false,
    "playwright-recorder": false,
};
