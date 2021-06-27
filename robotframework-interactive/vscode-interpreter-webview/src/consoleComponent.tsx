import * as React from 'react';
import * as monaco from 'monaco-editor';
import MonacoEditor from 'react-monaco-editor';
import { detectBaseTheme } from './themeDetector';

class IConsoleProps {
    handleEvaluate: (code: string, codeAsHtml: string) => Promise<void>
}

class _History {
    private readonly entries: string[] = [];
    private position: number = 0;

    public push(code: string) {
        if (this.entries.length > 0) {
            if (code === this.entries[this.entries.length - 1]) {
                // Don't add 2 equal entries one after the other.
                this.position = this.entries.length;
                return;
            }
        }
        this.entries.push(code);
        this.position = this.entries.length;
    }

    public getPrev(prefix: string): string | undefined {
        if (this.entries.length === 0) {
            return undefined;
        }
        if (this.position === 0) {
            return undefined;
        }
        let pos = this.position - 1;
        while (pos >= 0) {
            let value = this.entries[pos];
            if (value.startsWith(prefix)) {
                this.position = pos;
                return value;
            }
            pos -= 1;
        }
        return undefined;
    }

    public getNext(prefix: string): string | undefined {
        if (this.entries.length === 0) {
            return undefined;
        }
        if (this.position >= this.entries.length) {
            return undefined;
        }

        let pos = this.position + 1;
        while (pos < this.entries.length) {
            let value = this.entries[pos];
            if (value.startsWith(prefix)) {
                this.position = pos;
                return value;
            }
            pos += 1;
        }
        return undefined;
    }

    public resetPos() {
        this.position = this.entries.length;
    }

}

export class ConsoleComponent extends React.Component<IConsoleProps> {

    private history: _History = new _History();

    constructor(props) {
        super(props);
    }

    render() {
        let handleEvaluate = this.props.handleEvaluate;
        let history = this.history;

        function lineNumbers(line: number) {
            return '>';
        }

        function editorDidMount(editor: monaco.editor.IStandaloneCodeEditor) {
            function replaceAllInEditor(text: string, keepSelectionUnchanged: boolean) {
                editor.pushUndoStop();
                let model = editor.getModel();
                let endCursorState = undefined;
                if (keepSelectionUnchanged) {
                    endCursorState = [editor.getSelection()];
                }
                editor.executeEdits(
                    undefined,
                    [{ 'range': model.getFullModelRange(), 'text': text, 'forceMoveMarkers': true }],
                    endCursorState
                )
                editor.pushUndoStop();
            }

            // See: 
            // https://github.com/microsoft/vscode/blob/2f5fb0fe0ccca4fe2076b1ed16643895d14cdb98/src/vs/editor/common/editorContextKeys.ts
            // https://github.com/microsoft/vscode/blob/a2c4a0ca8ca8b86e8dd32e20e596a2e00bfdeaf9/src/vs/editor/contrib/suggest/suggest.ts
            // https://github.com/microsoft/vscode/blob/bfccdcb958130748419e6df1693c0f99d636dccf/src/vs/platform/contextkey/common/contextkeys.ts   
            // https://github.com/microsoft/vscode/search?q=RawContextKey
            // for some default context keys.

            let contextKey = editor.createContextKey('inFirstLine', false);

            editor.onDidChangeCursorSelection(() => {
                let selection = editor.getSelection();
                let pos = selection.getPosition();
                contextKey.set(pos.lineNumber == 1);
            });

            function getTextToCursor() {
                let selection = editor.getSelection();
                let pos = selection.getPosition();
                let range = {
                    startLineNumber: 1,
                    startColumn: 1,
                    endLineNumber: pos.lineNumber,
                    endColumn: pos.column
                }
                return editor.getModel().getValueInRange(range);
            }

            editor.addAction({
                id: 'Evaluate',
                label: 'Evaluate',
                precondition: null,
                keybindingContext: null,
                contextMenuGroupId: 'navigation',
                // keybindings: [monaco.KeyMod.Shift | monaco.KeyCode.Enter],
                keybindings: [monaco.KeyCode.Enter],
                run: async () => {
                    let value = editor.getValue();
                    let x: any = editor; // hack to get access to the _modelData.
                    let codeAsHtml = x._modelData.viewModel.getRichTextToCopy([editor.getModel().getFullModelRange()], false)
                    history.push(value);
                    replaceAllInEditor('', false);
                    await handleEvaluate(value, codeAsHtml.html);
                }
            });

            editor.addCommand(monaco.KeyCode.Tab, () => {
                // Add 4 spaces on tab.
                let selection = editor.getSelection();
                editor.executeEdits(
                    undefined,
                    [{ 'range': selection, 'text': '    ', 'forceMoveMarkers': true }],
                )
            }, 'editorTextFocus && !editorTabMovesFocus && !editorHasSelection && !inSnippetMode && !suggestWidgetVisible');

            editor.addCommand(monaco.KeyCode.UpArrow, () => {
                let prev = history.getPrev(getTextToCursor());
                if (prev === undefined) {
                    return;
                }
                replaceAllInEditor(prev, true);
            }, 'editorTextFocus && !editorHasSelection && inFirstLine');

            editor.addCommand(monaco.KeyCode.DownArrow, () => {
                let next = history.getNext(getTextToCursor());
                if (next === undefined) {
                    return;
                }
                replaceAllInEditor(next, true);
            }, 'editorTextFocus && !editorHasSelection && inFirstLine');

            editor.addCommand(monaco.KeyCode.Escape, () => {
                // Esc clears the editor and resets the history position.
                replaceAllInEditor('', false);
                history.resetPos();
            }, 'editorTextFocus');
        }

        let theme: string = detectBaseTheme();
        const options = {
            selectOnLineNumbers: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            lineNumbers: lineNumbers,
            scrollbar: { alwaysConsumeMouseWheel: false },
            'semanticHighlighting.enabled': true
        };

        return (
            <MonacoEditor
                language="robotframework-ls"
                theme={theme}
                value={null} // This will prevent any automatic update of the code.
                options={options}
                editorDidMount={editorDidMount}
            />
        );
    }
}