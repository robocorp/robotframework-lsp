// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

"use strict";

let lastTheme = undefined;

function logAndReturn(themeName: "my-light" | "my-dark" | "my-hc", reason: string): "my-light" | "my-dark" | "my-hc" {
    if (lastTheme !== themeName) {
        lastTheme = themeName;
        console.log("Using theme: " + themeName + " (" + reason + ")");
    }
    return themeName;
}

// Based on:
// https://stackoverflow.com/questions/37257911/detect-light-dark-theme-programatically-in-visual-studio-code
// Note: converts the name to the one expected by monaco.

let foundInBody: "my-light" | "my-dark" | "my-hc" | undefined = undefined;

export function detectBaseTheme(): "my-light" | "my-dark" | "my-hc" {
    if (foundInBody !== undefined) {
        return foundInBody;
    }
    const body = document.body;

    let reason = "No body found when detecting base theme (using dark by default).";
    if (body) {
        reason = "Computing base theme based on: " + body.className;
        switch (body.className) {
            case "vscode-light":
                foundInBody = logAndReturn("my-light", reason);
            case "vscode-dark":
                foundInBody = logAndReturn("my-dark", reason);
            case "vscode-high-contrast":
                foundInBody = logAndReturn("my-hc", reason);
        }
        if (foundInBody !== undefined) {
            return foundInBody;
        }
    }

    return logAndReturn("my-dark", reason);
}
