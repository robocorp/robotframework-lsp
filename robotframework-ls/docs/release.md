
Steps to do a new release
---------------------------

- Open a shell at the proper place (something as `X:\robocorpws\robotframework-lsp\robotframework-ls`)

- Create release branch (`git branch -D release-robotframework-lsp&git checkout -b release-robotframework-lsp`)

- Update version (`python -m dev set-version 1.10.0`).

- Update README.md to add notes on features/fixes (on `robotframework-ls` and `robotframework-intellij`).

- Update changelog.md to add notes on features/fixes and set release date (on `robotframework-ls` and `robotframework-intellij`).

- Update build.gradle version and patchPluginXml.changeNotes with the latest changelog (html expected).
  - Use `https://markdowntohtml.com/` to convert the changelog to HTML.

- Push contents, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.
  - `mu acp Robot Framework Language Server Release 1.10.0`

- Rebase with master (`git checkout master&git rebase release-robotframework-lsp`).

- Create a tag (`git tag robotframework-lsp-1.10.0`) and push it.

- Send release msg. i.e.:

Hi @channel,

I'm happy to announce the release of `Robot Framework Language Server 1.10.0`.

### New features

- Code action: Surround with try..except.
- Code action: Surround with try..except..finally.
- Interactive Console: (Robot Framework 4 onwards): When a single keyword call is executed and it has a non-None return, its return value is printed.
- Interactive Console: Typing a variable in the `Interactive Console` shows that variable. [#871](https://github.com/robocorp/robotframework-lsp/issues/871)
- Improve `IF`/`WHILE`/`Run Keyword If` snippet completions to make it a bit clearer that python expressions are expected.
- Building the model of the flow explorer no longer times out and a progress dialog is shown while building it.
- `robot.libraries.blacklist` can be used to blacklist libraries which should never appear in code-completion.
- Deprecated libraries:
    - `robot.libraries.deprecated` can be used to mark libraries as deprecated.
    - Keywords from deprecated libraries will not appear in the auto-import code-completion (so, they'll only be available if the `Library` is added to the `Settings`).
    - Libraries which start with `*DEPRECATED*` in its doc are also considered deprecated.
    - Keywords from libraries marked as deprecated will be shown as deprecated.
- Requesting completions right after `Libraries   ` without any additional name will show completions for all known (pre-loaded) libraries.
- Completions for variables are shown without having to enter `$` nor `${`.


### Bugfixes

- Properly report about undefined variable in `RETURN`. [#865](https://github.com/robocorp/robotframework-lsp/issues/865)
- References to variables used in `Evaluate` arguments are now properly collected.
- Don't show completion for the variable being currently defined in variable assign. 

Official clients supported: `VSCode` and `Intellij`.
Other editors supporting language servers can get it with: `pip install robotframework-lsp`.

Install `Robot Framework Language Server` from the respective marketplace or from one of the links below.
Links: [VSCode](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp), [Intellij](https://plugins.jetbrains.com/plugin/16086-robot-framework-language-server/versions/stable/) , [OpenVSX](https://open-vsx.org/extension/robocorp/robotframework-lsp), [PyPI](https://pypi.org/project/robotframework-lsp/), [GitHub (sources)](https://github.com/robocorp/robotframework-lsp/tree/master/robotframework-ls)