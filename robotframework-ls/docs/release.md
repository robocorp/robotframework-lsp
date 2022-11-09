
Steps to do a new release
---------------------------

- Open a shell at the proper place (something as `X:\vscode-robot\robotframework-lsp\robotframework-ls`)

- Create release branch (`git branch -D release-robotframework-lsp&git checkout -b release-robotframework-lsp`)

- Update version (`python -m dev set-version 1.5.0`).

- Update README.md to add notes on features/fixes (on `robotframework-ls` and `robotframework-intellij`).

- Update changelog.md to add notes on features/fixes and set release date (on `robotframework-ls` and `robotframework-intellij`).

- Update build.gradle version and patchPluginXml.changeNotes with the latest changelog (html expected).

- Push contents, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.
  - `mu acp Robot Framework Language Server Release 1.5.0`

- Rebase with master (`git checkout master&git rebase release-robotframework-lsp`).

- Create a tag (`git tag robotframework-lsp-1.5.0`) and push it.

- Send release msg. i.e.:

Hi @channel,

I'm happy to announce the release of `Robot Framework Language Server 1.5.0`.

*## New features*


*## Bugfixes*

- Snippets take into account the value of `robot.completions.keywords.argumentsSeparator`. [#723](https://github.com/robocorp/robotframework-lsp/issues/723)
- Completions properly presented for `Variables` under `*** Settings ***`. [#744](https://github.com/robocorp/robotframework-lsp/issues/744)
- *[VSCode]* Flow Explorer can now follow keywords defined in other files.


Official clients supported: `VSCode` and `Intellij`.
Other editors supporting language servers can get it with: `pip install robotframework-lsp`.

Install `Robot Framework Language Server` from the respective marketplace or from one of the links below.
Links: [VSCode](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp), [Intellij](https://plugins.jetbrains.com/plugin/16086-robot-framework-language-server/versions/stable/) , [OpenVSX](https://open-vsx.org/extension/robocorp/robotframework-lsp), [PyPI](https://pypi.org/project/robotframework-lsp/), [GitHub (sources)](https://github.com/robocorp/robotframework-lsp/tree/master/robotframework-ls)