import * as monaco from 'monaco-editor';
import { IRequestMessage, nextMessageSeq, sendRequestToClient } from './vscodeComm';

// Interesting references:
// https://microsoft.github.io/monaco-editor/playground.html
// https://github.com/Microsoft/monaco-languages
// https://microsoft.github.io/monaco-editor/monarch.html  (for tokens available/docs)
// https://microsoft.github.io/monaco-editor/playground.html#extending-language-services-semantic-tokens-provider-example

// This is what we receive from the language server.
const TOKEN_TYPES_FROM_LS = [
    "variable",
    "comment",
    "header",
    "setting",
    "name",
    "keywordNameDefinition",
    "variableOperator",
    "keywordNameCall",
    "settingOperator",
    "control",
    "testCaseName",
    "parameterName",
    "argumentValue",
]

export function configureMonacoLanguage() {
    const LANGUAGE_ID = 'robotframework-ls';
    monaco.languages.register({ id: LANGUAGE_ID });
    monaco.languages.setMonarchTokensProvider(LANGUAGE_ID, {
        tokenizer: {
            root: [
                [/^\*\*\*.*?\*\*\*/, "type"],
                [/^(\s)*#.*/, 'comment'],
                [/(\s\s|\t)#.*/, 'comment'],
            ]
        },
        ignoreCase: true,
    });


    monaco.languages.registerCompletionItemProvider(LANGUAGE_ID, {
        async provideCompletionItems(
            model: monaco.editor.ITextModel,
            position: monaco.Position,
            context: monaco.languages.CompletionContext,
            token: monaco.CancellationToken): Promise<monaco.languages.CompletionList> {

            let code = model.getValue();
            let msg: IRequestMessage = {
                'type': 'request',
                'seq': nextMessageSeq(),
                'command': 'completions',
            };
            msg['arguments'] = {
                'code': code,
                'position': position,
                'context': context,
            }
            let response = await sendRequestToClient(msg);
            if (!response.body) {
                let lst: monaco.languages.CompletionList = {
                    suggestions: [],
                }
                return lst;
            }
            let lst: monaco.languages.CompletionList = response.body;
            return lst;
        }
    });

    monaco.languages.registerDocumentSemanticTokensProvider(LANGUAGE_ID, {
        getLegend: function () {
            return {
                tokenTypes: TOKEN_TYPES_FROM_LS,
                tokenModifiers: []
            };
        },

        provideDocumentSemanticTokens: async function (model, lastResultId, token) {
            let msg: IRequestMessage = {
                'type': 'request',
                'seq': nextMessageSeq(),
                'command': 'semanticTokens',
            };
            let code = model.getValue()
            if (!code) {
                return {
                    data: new Uint32Array([]),
                    resultId: null
                };
            }
            msg['arguments'] = {
                'code': code,
            }
            let response = await sendRequestToClient(msg);
            if (response.body) {
                return response.body;
            }

            return {
                data: new Uint32Array([]),
                resultId: null
            };
        },

        releaseDocumentSemanticTokens: function (resultId) { }
    });

    monaco.editor.defineTheme('my-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'variable', foreground: '9CDCFE' },
            { token: 'comment', foreground: '6A9955' },
            { token: 'header', foreground: '4EC9B0' },
            { token: 'setting', foreground: '569CD6' },
            { token: 'name', foreground: '4EC9B0' },
            { token: 'variableOperator', foreground: 'D4D4D4' },
            { token: 'settingOperator', foreground: 'D4D4D4' },
            { token: 'keywordNameDefinition', foreground: 'DCDCAA' },
            // { token: 'keywordNameCall', foreground: '' }, // default foreground
            { token: 'control', foreground: 'C586C0' },
            { token: 'testCaseName', foreground: 'DCDCAA' },
            { token: 'parameterName', foreground: '9CDCFE' },
            { token: 'argumentValue', foreground: 'CE9178' },
        ],
        colors: {}
    });

    monaco.editor.defineTheme('my-light', {
        base: 'vs',
        inherit: true,
        rules: [
            { token: 'variable', foreground: '0000FF' },
            { token: 'comment', foreground: '008000' },
            { token: 'header', foreground: '800000', fontStyle: 'bold' },
            { token: 'setting', foreground: '0000FF' },
            { token: 'name', foreground: '000080' },
            { token: 'variableOperator', foreground: '0000FF' },
            { token: 'settingOperator', foreground: '0000FF' },
            { token: 'keywordNameDefinition', foreground: '098658' },
            // { token: 'keywordNameCall', foreground: '' }, // default foreground
            { token: 'control', foreground: '0000FF' },
            { token: 'testCaseName', foreground: '0000FF' },
            { token: 'parameterName', foreground: '098658' },
            { token: 'argumentValue', foreground: 'A31515' },
        ],
        colors: {}
    });

    monaco.editor.defineTheme('my-hc', {
        base: 'hc-black',
        inherit: true,
        rules: [
            { token: 'variable', foreground: '9CDCFE' },
            { token: 'comment', foreground: '6A9955' },
            { token: 'header', foreground: '4EC9B0' },
            { token: 'setting', foreground: '569CD6' },
            { token: 'name', foreground: '4EC9B0' },
            { token: 'variableOperator', foreground: 'D4D4D4' },
            { token: 'settingOperator', foreground: 'D4D4D4' },
            { token: 'keywordNameDefinition', foreground: 'DCDCAA' },
            // { token: 'keywordNameCall', foreground: '' }, // default foreground
            { token: 'control', foreground: 'C586C0' },
            { token: 'testCaseName', foreground: 'DCDCAA' },
            { token: 'parameterName', foreground: '9CDCFE' },
            { token: 'argumentValue', foreground: 'CE9178' },
        ],
        colors: {}
    });
}