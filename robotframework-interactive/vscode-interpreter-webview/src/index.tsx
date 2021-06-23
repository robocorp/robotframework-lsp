import * as React from 'react';
import * as ReactDOM from 'react-dom';
import * as monaco from 'monaco-editor';
import MonacoEditor from 'react-monaco-editor';
import SplitPane from 'react-split-pane';

import './style.css';
import { detectBaseTheme } from './themeDetector';
import spinner from "./spinner.svg";
import { IEvaluateMessage, nextMessageSeq, sendRequestToClient, eventToHandler, IOutputEvent, sendEventToClient } from './vscodeComm';
import { configureMonacoLanguage } from './monacoConf';

interface ICellInfo {
    id: number
    cellCode: string
}

interface ICellsContainer {
    cells: ICellInfo[]
}

interface IAppState extends ICellsContainer {
    showProgress: number
}

interface IHistoryProps extends ICellsContainer {
    showProgress: number
}

interface ICellProps {
    cellInfo: ICellInfo
}

class Cell extends React.Component<ICellProps> {
    render() {
        return (
            <div className="cell">
                <pre>
                    {this.props.cellInfo.cellCode}
                </pre>
            </div>
        );
    }
}


let _lastCellId: number = 0;
function nextCellId(): number {
    _lastCellId += 1;
    return _lastCellId;
}

class History extends React.Component<IHistoryProps> {

    progressRef: any

    constructor(props) {
        super(props)
        this.progressRef = React.createRef();
    }

    render() {
        const cells = this.props.cells.map((cellInfo: ICellInfo) => (
            <Cell key={cellInfo.id} cellInfo={cellInfo} />
        ));
        return (
            <div className="history">
                {cells}
                {this.props.showProgress ? <img src={spinner} width="50px;" height="50px;" ref={this.progressRef} /> : null}
            </div>
        );
    }

    componentDidUpdate() {
        if (this.props.showProgress) {
            let curr = this.progressRef.current;
            if (curr) {
                let container = curr.closest(".Pane1");

                if (container.scrollHeight > container.clientHeight) {
                    curr.scrollIntoView({ behavior: 'smooth' });
                }
            }
        }
    }
}

class IConsoleProps {
    handleEvaluate: (code: string) => Promise<void>
}

class Console extends React.Component<IConsoleProps> {

    constructor(props) {
        super(props);
    }

    render() {
        let handleEvaluate = this.props.handleEvaluate;

        function lineNumbers(line: number) {
            return '>';
        }

        function editorDidMount(editor: monaco.editor.IStandaloneCodeEditor) {
            // let contextKey = editor.createContextKey('on_first_line', false);
            editor.addAction({
                id: 'Evaluate',
                label: 'Evaluate',
                precondition: null,
                keybindingContext: null,
                contextMenuGroupId: 'navigation',
                keybindings: [monaco.KeyMod.Shift | monaco.KeyCode.Enter],
                run: async () => {
                    let value = editor.getValue();
                    // Note: this will also destroy the undo-redo stack.
                    // We could keep it, but this seems fine (an arrow
                    // up on the first char should restore history entries).
                    editor.setValue("");
                    await handleEvaluate(value);
                }
            });
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
        // See: https://github.com/microsoft/monaco-editor/issues/1833 for info on adding custom coloring later on...
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


class App extends React.Component<object, IAppState> {
    constructor(props) {
        super(props);
        this.state = {
            cells: [],
            showProgress: 0
        };
        this.handleEvaluate = this.handleEvaluate.bind(this);
        eventToHandler['output'] = this.onOutput.bind(this)

        sendEventToClient({
            type: 'event',
            seq: nextMessageSeq(),
            event: 'initialized'
        });
    }

    async onOutput(msg: IOutputEvent) {
        this.setState((prevState, props) => {
            let newCell: ICellInfo = {
                id: nextCellId(),
                cellCode: msg.output
            };

            return {
                'cells': prevState.cells.concat([newCell]),
            };
        });
    }

    async handleEvaluate(code: string) {
        if (!code) {
            return;
        }
        this.setState((prevState, props) => {
            let newCell: ICellInfo = {
                id: nextCellId(),
                cellCode: code
            };

            return {
                'cells': prevState.cells.concat([newCell]),
                'showProgress': prevState.showProgress + 1
            };
        });

        let msg: IEvaluateMessage = {
            'type': 'request',
            'command': 'evaluate',
            'seq': nextMessageSeq(),
            'arguments': {
                'expression': code,
                'context': 'repl'
            }
        };
        let response = await sendRequestToClient(msg);
        console.log('response', response);

        this.setState((prevState, props) => {
            return {
                'showProgress': prevState.showProgress - 1
            };
        });

    }

    render() {
        return (
            <SplitPane split="horizontal" minSize={50} defaultSize={250} allowResize={true} primary='second'>
                <History cells={this.state.cells} showProgress={this.state.showProgress} />
                <Console handleEvaluate={this.handleEvaluate} />
            </SplitPane>
        );
    }
}

// Create our initial div and render everything inside it.
const e = document.createElement("div");
document.body.appendChild(e);

configureMonacoLanguage();

ReactDOM.render(
    <App />,
    e
);