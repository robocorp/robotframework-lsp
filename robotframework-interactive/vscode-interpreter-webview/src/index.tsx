import * as React from 'react';
import * as ReactDOM from 'react-dom';
import * as monaco from 'monaco-editor';
import MonacoEditor from 'react-monaco-editor';
import SplitPane from 'react-split-pane';

import './style.css';
import { detectBaseTheme } from './themeDetector';
import spinner from "./spinner.svg";

const e = document.createElement("div");
document.body.appendChild(e);

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


let _lastId: number = 0;
function nextId(): number {
    _lastId += 1;
    return _lastId;
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
            scrollbar: { alwaysConsumeMouseWheel: false }
        };
        // See: https://github.com/microsoft/monaco-editor/issues/1833 for info on adding custom coloring later on...
        return (
            <MonacoEditor
                language="json"
                theme={theme}
                value={null} // This will prevent any automatic update of the code.
                options={options}
                editorDidMount={editorDidMount}
            />
        );
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


class App extends React.Component<object, IAppState> {
    consoleId: number

    constructor(props) {
        super(props);
        this.state = {
            cells: [],
            showProgress: 0
        };
        this.handleEvaluate = this.handleEvaluate.bind(this);
        this.consoleId = nextId();
    }

    async handleEvaluate(code: string) {
        if (!code) {
            return;
        }
        this.setState((prevState, props) => {
            let newCell: ICellInfo = {
                id: nextId(),
                cellCode: code
            };

            return {
                'cells': prevState.cells.concat([newCell]),
                'showProgress': prevState.showProgress + 1
            };
        });

        // TODO: Send the contents to the shell.
        await sleep(2000);

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
                <Console key={this.consoleId} handleEvaluate={this.handleEvaluate} />
            </SplitPane>
        );
    }
}

ReactDOM.render(
    <App />,
    e
);