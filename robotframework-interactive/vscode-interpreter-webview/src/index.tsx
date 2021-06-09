import * as React from 'react';
import * as ReactDOM from 'react-dom';
import MonacoEditor from 'react-monaco-editor';
import SplitPane from 'react-split-pane';

import './style.css';

const e = document.createElement("div");
document.body.appendChild(e);


class History extends React.Component {
  render() {
    return (
      <div className="history">
        <h1>History</h1>
      </div>
    );
  }
}

class Console extends React.Component {
  render() {
    function lineNumbers(line: number){
        return '>';
    }
    const code = "";
    const options = {
      selectOnLineNumbers: true,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      automaticLayout: true,
      lineNumbers: lineNumbers,
      scrollbar: { alwaysConsumeMouseWheel: false }
    };
    return (
      <MonacoEditor
        language="javascript"
        theme="vs-dark"
        value={code}
        options={options}
//         onChange={::this.onChange}
//         editorDidMount={::this.editorDidMount}
      />
    );
  }
}

class App extends React.Component {
  render() {
    return (
      <SplitPane split="horizontal" minSize={50} defaultSize={250} allowResize={true} primary='second'>
        <History/>
        <Console/>
      </SplitPane>
    );
  }
}

ReactDOM.render(
    <App/>,
    e
);