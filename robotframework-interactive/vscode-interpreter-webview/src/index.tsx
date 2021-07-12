import * as React from 'react';
import * as ReactDOM from 'react-dom';
import SplitPane from 'react-split-pane';
import { ConsoleComponent, FONT_INFO } from './consoleComponent';

import './style.css';
import spinner from "./spinner.svg";
import { IEvaluateMessage, nextMessageSeq, sendRequestToClient, eventToHandler, IOutputEvent, sendEventToClient, requestToHandler, codeAsHtml } from './vscodeComm';
import { configureMonacoLanguage } from './monacoConf';
import { monaco } from 'react-monaco-editor';

interface ICellInfo {
    id: number
    type: 'code' | 'stdout' | 'stderr' | 'info'
    cellCode: string
    cellCodeHtml: string
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

interface IEvaluateRequest {
    uri: string
    code: string
}

class CellComponent extends React.Component<ICellProps> {
    render() {
        let className = "cell_" + this.props.cellInfo.type;
        if (this.props.cellInfo.cellCodeHtml) {
            return <div className={className} dangerouslySetInnerHTML={{ __html: this.props.cellInfo.cellCodeHtml }}></div>;
        } else {
            return <div className={className}>
                <pre className="cell_output_content">
                    {this.props.cellInfo.cellCode}
                </pre>
            </div>
        }
    }
}


let _lastCellId: number = 0;
function nextCellId(): number {
    _lastCellId += 1;
    return _lastCellId;
}

class HistoryComponent extends React.Component<IHistoryProps> {

    progressRef: any

    constructor(props) {
        super(props)
        this.progressRef = React.createRef();
    }

    render() {
        const cells = this.props.cells.map((cellInfo: ICellInfo) => (
            <CellComponent key={cellInfo.id} cellInfo={cellInfo} />
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


class AppComponent extends React.Component<object, IAppState> {
    constructor(props) {
        super(props);
        this.state = {
            cells: [],
            showProgress: 0
        };
        this.handleEvaluate = this.handleEvaluate.bind(this);
        eventToHandler['output'] = this.onEventOutput.bind(this);
        requestToHandler['evaluate'] = this.onRequestEvaluate.bind(this);

        sendEventToClient({
            type: 'event',
            seq: nextMessageSeq(),
            event: 'initialized'
        });
    }

    async onEventOutput(msg: IOutputEvent) {
        this.setState((prevState, props) => {
            let type: 'stdout' | 'stderr' | 'info' = 'stdout';
            switch (msg.category) {
                case 'stderr':
                case 'stdout':
                case 'info':
                    type = msg.category;
            }
            if (prevState.cells.length > 0) {
                // Let's see if it should be joined to the last one...
                let lastCell: ICellInfo = prevState.cells[prevState.cells.length - 1];
                if (lastCell.type == type) {
                    lastCell.cellCode += msg.output;
                    return {
                        'cells': prevState.cells
                    };
                }
            }
            let newCell: ICellInfo = {
                id: nextCellId(),
                type: type,
                cellCode: msg.output,
                cellCodeHtml: undefined
            };
            return {
                'cells': prevState.cells.concat([newCell]),
            };

        });
    }

    // i.e.: VSCode can send something to be evaluated in the webview.
    async onRequestEvaluate(msg: IEvaluateRequest) {
        let code = msg['body'].code;
        await this.handleEvaluate(code, await codeAsHtml(code));
    }

    async handleEvaluate(code: string, codeAsHtml: string) {
        if (!code) {
            return;
        }
        this.setState((prevState, props) => {
            let newCell: ICellInfo = {
                id: nextCellId(),
                type: 'code',
                cellCode: code,
                cellCodeHtml: codeAsHtml,
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
            <SplitPane split="horizontal" minSize={50} defaultSize={50} allowResize={true} primary='second'>
                <HistoryComponent cells={this.state.cells} showProgress={this.state.showProgress} />
                <ConsoleComponent handleEvaluate={this.handleEvaluate} />
            </SplitPane>
        );
    }
}

// Create our initial div and render everything inside it.
const e = document.createElement("div");
document.body.appendChild(e);

configureMonacoLanguage();

ReactDOM.render(
    <AppComponent />,
    e
);