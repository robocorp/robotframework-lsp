import * as monaco from 'monaco-editor';

// Interesting references:
// https://microsoft.github.io/monaco-editor/playground.html
// https://github.com/Microsoft/monaco-languages
// https://microsoft.github.io/monaco-editor/monarch.html  (for tokens available/docs)
// https://microsoft.github.io/monaco-editor/playground.html#extending-language-services-semantic-tokens-provider-example
export function configureMonacoEditor(){
    monaco.languages.register({ id: 'robotframework-ls' });
    monaco.languages.setMonarchTokensProvider('robotframework-ls', {
        tokenizer: {
            root: [
                [/^\*\*\*.*?\*\*\*/, "type"],
                [/^(\s)*#.*/, 'comment'],
                [/(\s\s|\t)#.*/, 'comment'],
            ]
        },
        ignoreCase: true,
    });
}