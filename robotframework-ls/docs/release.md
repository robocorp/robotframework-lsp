
Steps to do a new release
---------------------------

- Open a shell at the proper place (something as `X:\robocorpws\robotframework-lsp\robotframework-ls`)

- Create release branch (`git branch -D release-robotframework-lsp&git checkout -b release-robotframework-lsp`)

- Update version (`python -m dev set-version 1.9.0`).

- Update README.md to add notes on features/fixes (on `robotframework-ls` and `robotframework-intellij`).

- Update changelog.md to add notes on features/fixes and set release date (on `robotframework-ls` and `robotframework-intellij`).

- Update build.gradle version and patchPluginXml.changeNotes with the latest changelog (html expected).
  - Use `https://markdowntohtml.com/` to convert the changelog to HTML.

- Push contents, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.
  - `mu acp Robot Framework Language Server Release 1.9.0`

- Rebase with master (`git checkout master&git rebase release-robotframework-lsp`).

- Create a tag (`git tag robotframework-lsp-1.9.0`) and push it.

- Send release msg. i.e.:

Hi @channel,

I'm happy to announce the release of `Robot Framework Language Server 1.9.0`.

### New features

- New snippet completions for WHILE without limit, CONTINUE, BREAK, RETURN, ELSE. [#856](https://github.com/robocorp/robotframework-lsp/issues/856)
- New line customization:
    - If a line starts with `#` if a new line is entered before the end of the line a `#` is added in the new line
    - If a line is split a continuation (`...`) is added.
- Quick fix: create `local variable` from an `undefined variable`.
- Quick fix: create `variable in the variables section` from an `undefined variable`.
- Quick fix: create `argument` from an `undefined variable`.
- Code action: assign to variable.
- Refactoring: extract `local variable`.
- Refactoring: extract `variable` to `variables section`.

### Bugfixes

- Text ranges when dealing with emoji unicode characters are now correct. [#862](https://github.com/robocorp/robotframework-lsp/issues/862)  
- Code analysis fix:  An arguments with a name with '=' must match a star arg with the full name if the name was already found (in RF keyword and not python method). [#860](https://github.com/robocorp/robotframework-lsp/issues/860)


Official clients supported: `VSCode` and `Intellij`.
Other editors supporting language servers can get it with: `pip install robotframework-lsp`.

Install `Robot Framework Language Server` from the respective marketplace or from one of the links below.
Links: [VSCode](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp), [Intellij](https://plugins.jetbrains.com/plugin/16086-robot-framework-language-server/versions/stable/) , [OpenVSX](https://open-vsx.org/extension/robocorp/robotframework-lsp), [PyPI](https://pypi.org/project/robotframework-lsp/), [GitHub (sources)](https://github.com/robocorp/robotframework-lsp/tree/master/robotframework-ls)