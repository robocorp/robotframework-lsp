import * as monaco from 'monaco-editor';

// Interesting references:
// https://microsoft.github.io/monaco-editor/playground.html
// https://github.com/Microsoft/monaco-languages
// https://microsoft.github.io/monaco-editor/monarch.html  (for tokens available/docs)
// https://microsoft.github.io/monaco-editor/playground.html#extending-language-services-semantic-tokens-provider-example
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
}