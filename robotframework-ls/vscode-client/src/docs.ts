import { readFileSync } from "fs";
import * as vscode from "vscode";
import * as marked from "marked";
import { MarkupContent } from "vscode-languageclient";
import { OUTPUT_CHANNEL } from "./channel";
import { getExtensionRelativeFile } from "./files";
import { debounce } from "./common";

export function escaped(unsafe: string): string {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getRobotDocsWebviewContent(libdocInfo: any): string {
    const libraryLibdocJson = libdocInfo.libdoc_json;
    if (libraryLibdocJson) {
        // Ok, we're dealing with a library, use the robot documentation format.
        const activeColorTheme = vscode.window.activeColorTheme;
        const kind = activeColorTheme.kind;

        const templateFile = getExtensionRelativeFile("../../vscode-client/templates/robot_docs.html", true);
        let data = readFileSync(templateFile, "utf8");
        if (kind != vscode.ColorThemeKind.Light) {
            // dark or high-contrast, make the media-query to dark match the theme
            data = data.replaceAll("prefers-color-scheme: dark", "max-width: 10000px");
        }
        data = data.replaceAll("libdoc = ", "libdoc = " + JSON.stringify(libraryLibdocJson));
        return data;
    }

    // Not dealing with a library: we should have hover information.
    const contents: MarkupContent = libdocInfo.contents;
    if (contents.kind == "markdown") {
        return marked.parse(contents.value);
    }
    return escaped(contents.value);
}

interface IContents {
    isPlaceholder: boolean;
    html: string;
}

// Note: this is based on https://github.com/mattbierner/vscode-docs-view/blob/master/src/docsView.ts
// (not a full copy, but some parts/ideas were used -- license MIT, see third party notices).
export class RobotDocumentationViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = "robot.view.documentation";
    private static readonly pinnedContext = "robot.view.documentation.isPinned";

    private _view?: vscode.WebviewView;
    private _loading?: { cts: vscode.CancellationTokenSource };
    private _pinned = false;
    private _lastContents?: IContents;

    constructor(context: vscode.ExtensionContext) {
        context.subscriptions.push(
            vscode.window.onDidChangeActiveTextEditor(() => {
                this.update();
            })
        );

        context.subscriptions.push(
            vscode.window.onDidChangeTextEditorSelection(() => {
                this.update();
            })
        );
        this.update();
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
        };

        webviewView.onDidChangeVisibility(() => {
            if (this._view?.visible) {
                this.update();
            }
        });

        webviewView.onDidDispose(() => {
            this._view = undefined;
            this._lastContents = undefined;
        });

        this._lastContents = this._getHtmlPlaceholderForWebview();
        webviewView.webview.html = this._lastContents.html;

        this.update();
    }

    public pin() {
        this.updatePinned(true);
    }

    public unpin() {
        this.updatePinned(false);
    }

    private updatePinned(value: boolean) {
        if (this._pinned === value) {
            return;
        }

        this._pinned = value;
        vscode.commands.executeCommand("setContext", RobotDocumentationViewProvider.pinnedContext, value);

        this.update();
    }

    private _getHtmlPlaceholderForWebview(additional?: string | undefined): IContents {
        additional = additional || "";
        return {
            "html": `<!DOCTYPE html>
			<html lang="en">
			<body>
                Change the selection to show the documentation for the given selection.
                <br/>
                <ul>
                    <li>Select a library to show the full Robot docs for the library.</li>
                    <li>Select a keyword to show the documentation just for that keyword.</li>
                </ul>
                ${additional}
			</body>
			</html>`,
            isPlaceholder: true,
        };
    }

    private async update() {
        this.updateDebounced();
    }

    updateDebounced = debounce(() => {
        this._doUpdate();
    }, 500);

    private async _doUpdate() {
        if (!this._view) {
            return;
        }

        if (this._pinned) {
            return;
        }

        if (this._loading) {
            this._loading.cts.cancel();
            this._loading = undefined;
        }

        const loadingEntry = { cts: new vscode.CancellationTokenSource() };
        this._loading = loadingEntry;

        const updatePromise = (async () => {
            const contents = await this.getHtmlContentForActiveEditor(loadingEntry.cts.token);
            if (loadingEntry.cts.token.isCancellationRequested) {
                return;
            }

            if (this._loading !== loadingEntry) {
                return;
            }
            this._loading = undefined;

            if (this._view) {
                // i.e.: A new content which is a placeholder should not override an old non-placeholder content.
                if (
                    !contents.isPlaceholder ||
                    !this._lastContents ||
                    contents.isPlaceholder === this._lastContents.isPlaceholder
                ) {
                    this._lastContents = contents;
                    this._view.webview.html = contents.html;
                }
            }
        })();

        await Promise.race([
            updatePromise,

            new Promise<void>((resolve) => setTimeout(resolve, 250)).then(() => {
                if (loadingEntry.cts.token.isCancellationRequested) {
                    return;
                }
                return vscode.window.withProgress(
                    { location: { viewId: RobotDocumentationViewProvider.viewType } },
                    () => updatePromise
                );
            }),
        ]);
    }

    private async getHtmlContentForActiveEditor(token: vscode.CancellationToken): Promise<IContents> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return this._getHtmlPlaceholderForWebview("<p>Note: no active editor.</p>");
        }

        if (editor.document.languageId !== "robotframework") {
            return this._getHtmlPlaceholderForWebview(
                "<p>Note: no Robot Documentation available for non-robot file.</p>"
            );
        }

        const selection = editor.selection;
        if (!selection) {
            return this._getHtmlPlaceholderForWebview("<p>Note: no active selection.</p>");
        }

        if (token.isCancellationRequested) {
            return this._getHtmlPlaceholderForWebview("<p>Request cancelled.</p>");
        }

        const uri = vscode.window.activeTextEditor.document.uri.toString();
        try {
            let commandResult: any = await vscode.commands.executeCommand("robot.collectRobotDocumentation", {
                "uri": uri,
                "line": selection.anchor.line,
                "col": selection.anchor.character,
            });
            if (!commandResult) {
                return this._getHtmlPlaceholderForWebview("<p>Unable to compute documentation.</p>");
            }
            if (commandResult["success"]) {
                return {
                    html: getRobotDocsWebviewContent(commandResult.result),
                    isPlaceholder: false,
                };
            } else {
                return this._getHtmlPlaceholderForWebview("<p>" + commandResult["message"] + "</p>");
            }
        } catch (err) {
            let indent = "    ";
            if (err.message) {
                OUTPUT_CHANNEL.appendLine(indent + err.message);
            }
            if (err.stack) {
                let stack: string = "" + err.stack;
                OUTPUT_CHANNEL.appendLine(stack.replace(/^/gm, indent));
            }
        }

        return this._getHtmlPlaceholderForWebview("<p>Unable to compute documentation.</p>");
    }
}
