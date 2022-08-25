
Steps to do a new release
---------------------------

- Open a shell at the proper place (something as `X:\vscode-robot\robotframework-lsp\robotframework-ls`)

- Create release branch (`git branch -D release-robotframework-lsp&git checkout -b release-robotframework-lsp`)

- Update version (`python -m dev set-version 1.1.0`).

- Update README.md to add notes on features/fixes (on `robotframework-ls` and `robotframework-intellij`).

- Update changelog.md to add notes on features/fixes and set release date (on `robotframework-ls` and `robotframework-intellij`).

- Update build.gradle version and patchPluginXml.changeNotes with the latest changelog (html expected).

- Push contents, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.

- Rebase with master (`git checkout master&git rebase release-robotframework-lsp`).

- Create a tag (`git tag robotframework-lsp-1.1.0`) and push it.

- Send release msg. i.e.:

Hi @channel,

I'm happy to announce the release of `Robot Framework Language Server 1.1.0`.

*## New features*

- *[VSCode]* `Robot Flow Visualization`: a new visualization which shows the Robot execution as a graph (currently in the browser).
    - Generated for the tasks/tests in the current file through the command: `Robot Framework: Open Robot Flow Explorer`
- *[VSCode]* It's now possible to enable `Run/Debug` and `Interactive Console` code-lenses individually.
- *[Intellij]* When pressing space a completion is no longer applied automatically.
- *[Intellij]* The plugin will re-register file associations to `.resource` and `.robot`. [#605](https://github.com/robocorp/robotframework-lsp/issues/605)
- Code analysis setting to check if keyword is not used anywhere in the workspace.
    - Opt-in through the `robot.lint.unusedKeyword:true` setting. [#722](https://github.com/robocorp/robotframework-lsp/issues/722)
- An LRU based on file size now prevents unlimited usage of RAM when caching files loaded from the filesystem. [#720](https://github.com/robocorp/robotframework-lsp/issues/720)
    - It's possible to customize the size of the target memory for this LRU through the `RFLS_FILES_TARGET_MEMORY_IN_BYTES` environment variable.
- If a keyword call resolves to multiple keywords, the argument analysis is done for all the matches. [#724](https://github.com/robocorp/robotframework-lsp/issues/724).
- (Experimental) Support for localization in Robot Framework 5.1. [#728](https://github.com/robocorp/robotframework-lsp/issues/728).
    - The language may be set just for a file (with `language: <lang>` on the top of the file).
    - The language may be specified globally through the setting: `robot.language`.
    - Support for completions with translated section names and settings.
    - Support for syntax highlighting translated bdd prefixes.
    - The language(s) set in the `robot.language` configuration are automatically added as parameter on new launches.

*## Bugfixes*

- *[VSCode]* A non-string value is converted to string before expanding variables. [#727](https://github.com/robocorp/robotframework-lsp/issues/727)
- *[Intellij]* Fixed `NullPointerException` on hover. [#731](https://github.com/robocorp/robotframework-lsp/issues/731)
- *[Intellij]* `$Prompt$` macro properly replaced when launching. [#737](https://github.com/robocorp/robotframework-lsp/issues/737)
- Operations no longer timeout, rather, they just print to the log (as the timeouts weren't always ideal for slower machines). [#733](https://github.com/robocorp/robotframework-lsp/issues/733)
- Fixed issue where references wouldn't be found properly.
- Variables imported from module folder (`module/__init__.py`) are properly recognized. [#734](https://github.com/robocorp/robotframework-lsp/issues/734) 


Official clients supported: `VSCode` and `Intellij`.
Other editors supporting language servers can get it with: `pip install robotframework-lsp`.

Install `Robot Framework Language Server` from the respective marketplace or from one of the links below.
Links: [VSCode](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp), [Intellij](https://plugins.jetbrains.com/plugin/16086-robot-framework-language-server/versions/stable/) , [OpenVSX](https://open-vsx.org/extension/robocorp/robotframework-lsp), [PyPI](https://pypi.org/project/robotframework-lsp/), [GitHub (sources)](https://github.com/robocorp/robotframework-lsp/tree/master/robotframework-ls)