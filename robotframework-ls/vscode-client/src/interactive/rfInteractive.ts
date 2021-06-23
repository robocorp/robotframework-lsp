/**
 * The idea is doing an interactive shell for Robot Framework inside of VSCode.
 *
 * There is previous work on this in https://github.com/microsoft/vscode-jupyter.
 * 
 * Interesting docs related to webviews:
 * https://medium.com/younited-tech-blog/reactception-extending-vs-code-extension-with-webviews-and-react-12be2a5898fd
 * https://github.com/Ciaanh/reactception/
 * https://code.visualstudio.com/api/extension-guides/webview
 * https://marketplace.visualstudio.com/items?itemName=leocll.vscode-extension-webview-template
 * https://github.com/leocll/vscode-extension-webview-template
 */

import { commands, ExtensionContext, WebviewPanel, window } from "vscode";
import * as vscode from 'vscode';
import { LanguageClient } from "vscode-languageclient/node";
import { OUTPUT_CHANNEL } from "../extension";

const DEV = false;

function getWebviewOptions(localResourceRoot: vscode.Uri): vscode.WebviewOptions & vscode.WebviewPanelOptions {
    return {
        // Enable javascript in the webview
        enableScripts: true,

        // We may have a lot of context in the interactive shell webview, and it may be tricky to save/restore it all.
        retainContextWhenHidden: true,

        // And restrict the webview to only loading content from our extension's directory.
        localResourceRoots: [localResourceRoot]
    };
}

async function executeCheckedCommand(commandId: string, args: any) {
    try {
        return await commands.executeCommand(commandId, args);
    } catch (err) {
        return {
            'success': false,
            'message': '' + err,
            'result': undefined
        }
    }
}

class InteractiveShellPanel {
    // public static currentPanel: InteractiveShellPanel | undefined;

    public static readonly viewType = 'InteractiveShellPanel';

    private readonly _panel: vscode.WebviewPanel;
    private readonly _interpreterId: number;
    private readonly _localResourceRoot: vscode.Uri;
    public readonly disposables: vscode.Disposable[] = [];

    private _finishInitialized;
    public readonly initialized: Promise<boolean>;

    private _lastMessageId: number = 0;

    nextMessageSeq(): number {
        this._lastMessageId += 1;
        return this._lastMessageId;
    }

    public static async create(extensionUri: vscode.Uri, interpreterId: number): Promise<InteractiveShellPanel> {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        let localResourceRoot = vscode.Uri.joinPath(extensionUri, 'src', 'robotframework_ls', 'vendored', 'vscode-interpreter-webview');
        if (DEV) {
            localResourceRoot = vscode.Uri.file("X:/vscode-robot/robotframework-lsp/robotframework-interactive/vscode-interpreter-webview/dist")
        }

        // Otherwise, create a new panel.
        const panel = vscode.window.createWebviewPanel(
            InteractiveShellPanel.viewType,
            'Robot Framework Interpreter',
            column || vscode.ViewColumn.One,
            getWebviewOptions(localResourceRoot),
        );

        return new InteractiveShellPanel(panel, localResourceRoot, interpreterId);
    }

    private constructor(panel: vscode.WebviewPanel, localResourceRoot: vscode.Uri, interpreterId: number) {
        this._panel = panel;
        this._localResourceRoot = localResourceRoot;
        this._interpreterId = interpreterId;

        let interactiveShell = this;
        this.initialized = new Promise((resolve, reject) => {
            interactiveShell._finishInitialized = resolve;
        });

        // Set the webview's initial html content
        this._update();


        // Listen for when the panel is disposed
        // This happens when the user closes the panel or when the panel is closed programmatically
        this._panel.onDidDispose(() => this.dispose(), null, this.disposables);
        let webview = this._panel.webview;
        let nextMessageSeq = this.nextMessageSeq.bind(this);

        async function handleEvaluate(message) {
            let result: any = { 'success': false, 'message': '<error evaluating>', 'result': undefined };

            try {
                let code = message.arguments['expression'];
                result = await executeCheckedCommand("robot.internal.rfinteractive.evaluate", {
                    'interpreter_id': interpreterId,
                    'code': code
                });
            } catch (err) {
                OUTPUT_CHANNEL.appendLine('Error in evaluation: ' + err);
            } finally {
                let response: any = {
                    type: 'response',
                    seq: nextMessageSeq(),
                    command: message.command,
                    request_seq: message.seq,
                    body: '<evaluated from vscode>'
                }
                webview.postMessage(response); // Send the response, even if it was an error.
            }
            if (!result['success']) {
                window.showErrorMessage('Error evaluating in interactive console: ' + result['message'])
            }
        }

        async function handleSemanticTokens(message) {
            let result = undefined;
            try {
                let code = message.arguments['code'];
                // result is {'data': [...], 'resultId': ...}
                result = await commands.executeCommand("robot.internal.rfinteractive.semanticTokens", {
                    'interpreter_id': interpreterId,
                    'code': code
                });
            } catch (err) {
                OUTPUT_CHANNEL.appendLine('Error getting semantic tokens: ' + err);
            } finally {
                let response: any = {
                    type: 'response',
                    seq: nextMessageSeq(),
                    command: message.command,
                    request_seq: message.seq,
                    body: result
                }
                webview.postMessage(response);
            }
        }

        // Handle messages from the webview
        this._panel.webview.onDidReceiveMessage(
            async message => {
                if (message.type == 'request') {
                    let result = undefined;
                    switch (message.command) {
                        case 'evaluate':
                            await handleEvaluate(message);
                            return;

                        case 'semanticTokens':
                            await handleSemanticTokens(message);
                            return;
                    }
                } else if (message.type == 'event') {
                    if (message.event == 'initialized') {
                        interactiveShell._finishInitialized();
                    }
                }
            },
            null,
            this.disposables
        );
    }

    public onOutput(category: string, output: string) {
        this._panel.webview.postMessage({
            'type': 'event',
            'seq': this.nextMessageSeq(),
            'event': 'output',
            'category': category,
            'output': output
        });
    }

    public dispose() {
        // Clean up our resources
        this._panel.dispose();

        while (this.disposables.length) {
            const x = this.disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    private _update() {
        const webview = this._panel.webview;
        this._panel.webview.html = this._getHtmlForWebview(webview);
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        // Note: we can't really load from file://
        // See: https://github.com/microsoft/vscode/issues/87282
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this._localResourceRoot, 'bundle.js'));
        return `<!DOCTYPE html>
			<html lang="en">
			<head>
				<meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Robot Interactive Interpreter</title>
                <script>
                const vscode = acquireVsCodeApi();
                </script>
                <script defer src="${scriptUri}"></script>
            </head>
			<body style="padding: 0 0 0 0">
			</body>
			</html>`;
    }
}

export async function registerInteractiveCommands(context: ExtensionContext, languageClient: LanguageClient) {
    let extensionUri = context.extensionUri;

    async function createInteractiveShell() {
        let interpreterId = -1;
        let buffered: string[] = new Array();
        let interactiveShellPanel: undefined | InteractiveShellPanel = undefined;
        async function onOutput(args) {
            if (args['interpreter_id'] === interpreterId) {
                let category: string = args['category'];
                let output: string = args['output'];
                interactiveShellPanel?.onOutput(category, output);
            }
        }

        let disposeNotification = languageClient.onNotification("interpreter/output", (args) => {
            if (buffered !== undefined) {
                buffered.push(args);
            } else {
                onOutput(args);
            }
        });
        context.subscriptions.push(disposeNotification);

        // Note that during the creation, it's possible that we already have output, so, we
        // need to buffer anything up to the point where we actually have the interpreter.
        let result = await commands.executeCommand("robot.internal.rfinteractive.start");
        if (!result['success']) {
            window.showErrorMessage('Error creating interactive console: ' + result['message'])
            return;
        }
        interpreterId = result['result']['interpreter_id'];
        interactiveShellPanel = await InteractiveShellPanel.create(extensionUri, interpreterId);
        interactiveShellPanel.disposables.push(disposeNotification);

        OUTPUT_CHANNEL.appendLine('Waiting for Robot Framework Interactive Shell UI (id: ' + interpreterId + ') initialization.');
        await interactiveShellPanel.initialized;
        OUTPUT_CHANNEL.appendLine('Robot Framework Interactive Shell UI (id: ' + interpreterId + ') initialized.');
        while (buffered.length) {
            buffered.splice(0, buffered.length).forEach((el) => {
                onOutput(el);
            });
        }

        // Start sending contents directly to the interactive shell now that we processed the 
        // output backlog from the startup.
        buffered = undefined;
    }
    context.subscriptions.push(commands.registerCommand('robot.interactiveShell', createInteractiveShell));
}