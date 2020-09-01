import { window } from 'vscode';

export const OUTPUT_CHANNEL_NAME = "Robocorp Code";
export const OUTPUT_CHANNEL = window.createOutputChannel(OUTPUT_CHANNEL_NAME);
