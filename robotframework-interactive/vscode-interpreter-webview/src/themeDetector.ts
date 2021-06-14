// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

'use strict';

// Based on:
// https://stackoverflow.com/questions/37257911/detect-light-dark-theme-programatically-in-visual-studio-code
// Note: converts the name to the one expected by monaco.
export function detectBaseTheme(): 'vs' | 'vs-dark' | 'hc-black' {
    const body = document.body;

    if (body) {
        switch (body.className) {
            default:
            case 'vscode-light':
                return 'vs';
            case 'vscode-dark':
                return 'vs-dark';
            case 'vscode-high-contrast':
                return 'hc-black';
        }
    }

    return 'vs-dark';
}
