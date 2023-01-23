
Steps to do a new release
---------------------------

- Open a shell at the proper place (something as `X:\robocorpws\robotframework-lsp\robotframework-ls`)

- Create release branch (`git branch -D release-robotframework-lsp&git checkout -b release-robotframework-lsp`)

- Update version (`python -m dev set-version 1.8.0`).

- Update README.md to add notes on features/fixes (on `robotframework-ls` and `robotframework-intellij`).

- Update changelog.md to add notes on features/fixes and set release date (on `robotframework-ls` and `robotframework-intellij`).

- Update build.gradle version and patchPluginXml.changeNotes with the latest changelog (html expected).
  - Use `https://markdowntohtml.com/` to convert the changelog to HTML.

- Push contents, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.
  - `mu acp Robot Framework Language Server Release 1.8.0`

- Rebase with master (`git checkout master&git rebase release-robotframework-lsp`).

- Create a tag (`git tag robotframework-lsp-1.8.0`) and push it.

- Send release msg. i.e.:

Hi @channel,

I'm happy to announce the release of `Robot Framework Language Server 1.8.0`.

*## New features*

- It's possible to make a launch with a target in the arguments by specifying `<target-in-args>` as the target (useful if the target is in an arguments file).

*## Bugfixes*

- Properly collect references for keywords with variables in the name. [#827](https://github.com/robocorp/robotframework-lsp/issues/827)
- Add placeholders when completing keywords with variables in the name. [#824](https://github.com/robocorp/robotframework-lsp/issues/824)
- Find references for variables embedded in keywords. [#825](https://github.com/robocorp/robotframework-lsp/issues/825)
- Don't prefix module name for keywords in the current module. [#843](https://github.com/robocorp/robotframework-lsp/issues/843)
- Debugger: Fixed issue where the stack of the debugger could end up being unsynchronized.
- Debugger: If there's some error in a debugger callback, don't break execution. [#841](https://github.com/robocorp/robotframework-lsp/issues/841)


Official clients supported: `VSCode` and `Intellij`.
Other editors supporting language servers can get it with: `pip install robotframework-lsp`.

Install `Robot Framework Language Server` from the respective marketplace or from one of the links below.
Links: [VSCode](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp), [Intellij](https://plugins.jetbrains.com/plugin/16086-robot-framework-language-server/versions/stable/) , [OpenVSX](https://open-vsx.org/extension/robocorp/robotframework-lsp), [PyPI](https://pypi.org/project/robotframework-lsp/), [GitHub (sources)](https://github.com/robocorp/robotframework-lsp/tree/master/robotframework-ls)