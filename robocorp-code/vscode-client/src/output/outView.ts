import { TextDecoder } from "util";
import * as vscode from "vscode";
import { debounce } from "../common";
import { getExtensionRelativeFile, isFile, uriExists } from "../files";
import { globalOutputViewState } from "./outViewRunIntegration";

interface IContents {
    isPlaceholder: boolean;
    html: string;
    afterHTMLSet?: any;
}

export class RobotOutputViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = "robocorp.python.view.output";

    private view?: vscode.WebviewView;
    private loading?: { cts: vscode.CancellationTokenSource };
    private extensionUri: vscode.Uri;
    private localResourceRoot: vscode.Uri = undefined;

    // We can use this as a place to store the run results we've seen.
    private storageUri: vscode.Uri = undefined;

    constructor(context: vscode.ExtensionContext) {
        this.extensionUri = context.extensionUri;
        this.storageUri = context.storageUri;
        // Constructor is called only once, afterwards it just resolves...
        context.subscriptions.push(
            vscode.window.onDidChangeActiveTextEditor(() => {
                this.update();
            })
        );
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        token: vscode.CancellationToken
    ) {
        async function showSourceAtLineno(source, lineno) {
            lineno -= 1;
            const start = new vscode.Position(lineno, 0);
            const options = { selection: new vscode.Selection(start, start) };
            const editor = await vscode.window.showTextDocument(vscode.Uri.file(source), options);
        }
        this.view = webviewView;

        webviewView.webview.onDidReceiveMessage(async (message) => {
            if (message.type == "event") {
                if (message.event == "onClickReference") {
                    const data = message.data;
                    if (data) {
                        let source = data["source"];
                        let lineno: number = data["lineno"];
                        if (source && lineno && lineno > 0) {
                            showSourceAtLineno(source, lineno);
                        } else if (data["messageType"] === "ST") {
                            // Tests have a line but the source comes from the suite.
                            if (lineno && lineno > 0) {
                                const scope: any[] = data["scope"];
                                if (scope !== undefined && scope.length > 0) {
                                    const parentMsg = scope[0];
                                    source = parentMsg["decoded"].suite_source;
                                    if (source && isFile(source)) {
                                        showSourceAtLineno(source, lineno);
                                    }
                                }
                            }
                        }
                    }
                } else if (message.event === "onSetCurrentRunId") {
                    const data = message.data;
                    if (data) {
                        globalOutputViewState.setCurrentRunId(data["runId"]);
                    }
                }
            }
        });

        webviewView.onDidChangeVisibility(() => {
            if (!this.view || !this.view.visible) {
                globalOutputViewState.setWebview(undefined);
            } else {
                globalOutputViewState.setWebview(this.view.webview);
                globalOutputViewState.updateAfterVisible();
            }

            // Can be used in dev to update the whole HTML instead of just the contents.
            // this.updateHTML(undefined); //TODO: Comment this line when not in dev mode.
            this.update();
        });

        webviewView.onDidDispose(() => {
            globalOutputViewState.setWebview(undefined);
            this.view = undefined;
        });

        globalOutputViewState.setWebview(this.view.webview);
        this.updateHTML(token);
    }

    private async updateHTML(token: vscode.CancellationToken | undefined) {
        if (!this.localResourceRoot) {
            this.localResourceRoot = await getLocalResourceRoot(this.extensionUri);
        }
        const localResourceRoots = [];
        if (this.localResourceRoot) {
            localResourceRoots.push(this.localResourceRoot);
        }
        if (token?.isCancellationRequested) {
            return;
        }

        const webviewView = this.view;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: localResourceRoots,
        };

        let html: string;
        try {
            // const indexHTML: vscode.Uri = vscode.Uri.joinPath(this.localResourceRoot, "index.html");
            const templateFile = getExtensionRelativeFile("../../vscode-client/templates/output.html", true);
            const indexHTML: vscode.Uri = vscode.Uri.file(templateFile);
            const indexContents: Uint8Array = await vscode.workspace.fs.readFile(indexHTML);
            if (token?.isCancellationRequested) {
                return;
            }
            const decoded = new TextDecoder("utf-8").decode(indexContents);
            html = decoded;
        } catch (error) {
            html = "Error loading HTML: " + error;
        }
        webviewView.webview.html = html;
        globalOutputViewState.updateAfterVisible();

        this.update();
    }

    private async update() {
        this.updateDebounced();
    }

    updateDebounced = debounce(() => {
        this._doUpdate();
    }, 500);

    private async _doUpdate() {
        if (!this.view || !this.view.visible) {
            return;
        }

        if (this.loading) {
            this.loading.cts.cancel();
            this.loading = undefined;
        }

        const loadingEntry = { cts: new vscode.CancellationTokenSource() };
        this.loading = loadingEntry;

        const updatePromise = (async () => {
            if (this.loading !== loadingEntry) {
                return;
            }
            this.loading = undefined;

            if (this.view && this.view.visible) {
                this.onUpdatedEditorSelection(loadingEntry.cts.token);
            }
        })();

        await Promise.race([
            updatePromise,

            new Promise<void>((resolve) => setTimeout(resolve, 250)).then(() => {
                if (loadingEntry.cts.token.isCancellationRequested) {
                    return;
                }
                return vscode.window.withProgress(
                    { location: { viewId: RobotOutputViewProvider.viewType } },
                    () => updatePromise
                );
            }),
        ]);
    }

    private async onUpdatedEditorSelection(token: vscode.CancellationToken): Promise<IContents> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return;
        }

        if (token.isCancellationRequested) {
            return;
        }

        const filePath = editor.document.uri.fsPath;
        if (!filePath.endsWith(".robolog")) {
            return;
        }
        const currDoc = editor.document;

        let text = currDoc.getText();
        await globalOutputViewState.addRun(filePath, filePath, text);
    }
}

async function getLocalResourceRoot(extensionUri: vscode.Uri): Promise<vscode.Uri | undefined> {
    let localResourceRoot = vscode.Uri.file(getExtensionRelativeFile("../../vscode-client/templates", true));
    return localResourceRoot;
}
