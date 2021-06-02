New in 0.18.0 (2021-06-02)
-----------------------------

- Support for variables import:
  - Loads variables from `.py` and `.yaml` files.
- Semantic highlighting: equals sign no longer causes incorrect coloring on `catenate` keyword and `documentation` section.
- A module shadowing `builtin.py` no longer causes the default `Builtin` module not to be found anymore.
- Code analysis no longer throws error when dealing with a `Library` without a name declared. 
- Robocop updated to 1.7.1.


New in 0.17.0 (2021-05-24)
-----------------------------

- Variables may be used in settings. See the [related FAQ](https://github.com/robocorp/robotframework-lsp/blob/master/robotframework-ls/docs/faq.md#how-to-use-variables-in-settings) for details.
- Semantic highlighting was improved to differentiate the parameter (name) from the argument (value).
- Code-lens to run/debug suite is only shown if there are actually tests in the suite.
- Breakpoint improvements (condition, hitCondition, logMessage).
- Variables are now shown in the document outline.
- When launching a `.robot`, if a `__init__.robot` is present in the same directory, a `--suite` is done by default.
- Breakpoints are properly hit on `__init__.robot` files.
- Fixed issue which could lead to high-cpu due to filesystem polling.
  - It's now possible to set an environment variable `ROBOTFRAMEWORK_LS_POLL_TIME=<poll time in seconds>` to change the filesystem target poll time.
  - When possible, it's recommended to set an environment variable `ROBOTFRAMEWORK_LS_WATCH_IMPL=watchdog` to use native watches on Linux and MacOS (already default on Windows).
  - A file-observer is started as a separate process and multiple clients communicate with it.
  
 
New in 0.16.0 (2021-05-12)
-----------------------------

- Document symbols.
- It's possible to configure the casing of keywords from libraries used in code-completion.
- Launching/debugging improvements (VSCode):
  - Code lens with options to run/debug a test, task or suite.
  - Commands to run/debug a test, task or suite
  - Note: it's possible to configure the command/code lens launch by having a `Robot Framework: Launch template` launch config.
  - When a run is done in the internal terminal, provide hyperlinks to open html results in the browser.


New in 0.15.0 (2021-05-05)
-----------------------------

- Mixed-mode debugging:
  - Add line breakpoints in `.robot` or `.py` files.


New in 0.14.0 (2021-04-14)
-----------------------------

- Robocop linter is now opt-in instead of opt-out. [#312](https://github.com/robocorp/robotframework-lsp/issues/312)
- Add code-completion for `${CURDIR}`. [#313](https://github.com/robocorp/robotframework-lsp/issues/313)
- Use listener instead of monkey-patching when debugging (RF 4 onwards). [#310](https://github.com/robocorp/robotframework-lsp/issues/310)
- Silence exception from creating libspec for Dialogs module. [#93](https://github.com/robocorp/robotframework-lsp/issues/93)
- Search `PYTHONPATH` when looking to resolve relative paths in Imports. [#266](https://github.com/robocorp/robotframework-lsp/issues/266)

New in 0.13.1 (2021-04-08)
-----------------------------

- Resolve environment variables when trying to resolve libraries/resources paths (i.e.: `%{env_var}`). [#295](https://github.com/robocorp/robotframework-lsp/issues/295)
- Properly resolve variables for Library imports (not only Resource imports).

New in 0.12.0 (2021-04-01)
-----------------------------

- By default, fsnotify (polling) is now used on Linux and Mac and watchdog (native) on Windows due to resource usage limits on Linux and Mac.
  Using `watchdog` is still recommended when possible. See the [FAQ](https://github.com/robocorp/robotframework-lsp/blob/master/robotframework-ls/docs/faq.md#how-to-change-the-file-watch-mode)
  for details. 
- Code-folding is now available. [#288](https://github.com/robocorp/robotframework-lsp/issues/288)
- Hovering over keywords now shows its information.
- Code analysis with empty teardown works properly. [#289](https://github.com/robocorp/robotframework-lsp/issues/289)
- No longer recursing on local circular imports. [#269](https://github.com/robocorp/robotframework-lsp/issues/269)
- System directory separator `${/}` is recognized. [#153](https://github.com/robocorp/robotframework-lsp/issues/153)
- It's now possible to enable logging through a `ROBOTFRAMEWORK_LS_LOG_FILE` environment variable.
- [Robocop](https://robocop.readthedocs.io/en/latest/) fixes integrated (trailing blank line, misaligned variable).

New in 0.11.1 (2021-03-29)
-----------------------------

- [Robocop](https://robocop.readthedocs.io/en/latest/) updated to 1.6.1.
- Fixes in semantic syntax hightlighting with Robot Framework 3.x.
- Keywords from `Reserved.py` are no longer shown for auto-import.

New in 0.11.0 (2021-03-24)
-----------------------------

- [Robocop](https://robocop.readthedocs.io/en/latest/) is now used to lint (enabled by default, can be disabled in settings).
- Snippets completion is now properly case-insensitive.
- If there's some problem computing semantic tokens, log it and still return a valid value. [#274](https://github.com/robocorp/robotframework-lsp/issues/274)
- If a keyword name is defined in the context, don't try to create an auto-import for it.
- Reworded some settings to be clearer.

New in 0.10.0 (2021-03-19)
-----------------------------

- Fixed issue changing workspace folders.
- Added templates for `IF` statements.
- `FOR` templates no longer have a `/` in them.
- Added support for `semanticTokens/full` in the language server.
- Minimum VSCode version required is now `1.53.0`.

New in 0.9.1 (2021-03-10)
-----------------------------

- Support python packages as libraries (package/__init__.py). [#228](https://github.com/robocorp/robotframework-lsp/issues/228)

New in 0.9.0 (2021-03-03)
-----------------------------

- It's now possible to use polling instead of native filesystem notifications
  - It may be useful in case watchdog is having glitches.
  - To use it, set an environment variable: `ROBOTFRAMEWORK_LS_WATCH_IMPL=fsnotify`
- Gathering workspace symbols is much faster.
- Keyword completions should not be duplicated by the auto-import Keyword completions anymore. 

New in 0.8.0 (2021-02-16)
-----------------------------

- New setting: robot.workspaceSymbolsOnlyForOpenDocs for cases where code-completion is slow due to workspace symbols scanning. [#243](https://github.com/robocorp/robotframework-lsp/issues/243) 
- Don't offer completions for section names after 2 spaces of the section name.
- Debugger is working with the latest Robot Framework master.

New in 0.7.1 (2021-01-13)
-----------------------------

- Support for If/For statements in debugger with the master version of RobotFramework. [#232](https://github.com/robocorp/robotframework-lsp/issues/232)
- Properly handling case where parsing raised an Exception which could break code-completion and workspace symbols. [#231](https://github.com/robocorp/robotframework-lsp/issues/231)


New in 0.7.0 (2021-01-07)
-----------------------------

- Code completion for all keywords in the workspace with auto-import of Library or Resource. [#210](https://github.com/robocorp/robotframework-lsp/issues/210)
- When a space is at the end of a line when requesting a code-completion it's properly recognized as a part of the keyword.

New in 0.6.4 (2020-12-21)
-----------------------------

- When launching the language server, pick the version shipped and not the one installed in the target python [#91](https://github.com/robocorp/robotframework-lsp/issues/91)

New in 0.6.3 (2020-12-08)
-----------------------------

- watchdog binary dependencies are shipped along in Mac OS [#190](https://github.com/robocorp/robotframework-lsp/issues/190)

New in 0.6.2 (2020-12-02)
-----------------------------

- If libspec cannot be generated because docutils is not installed, force text mode. [#199](https://github.com/robocorp/robotframework-lsp/issues/199)
- Support libraries with the same basename but in different places. [#204](https://github.com/robocorp/robotframework-lsp/issues/204)

New in 0.6.1 (2020-11-29)
-----------------------------

- Performance improvement: Cache that libspec could not be created.

New in 0.6.0 (2020-11-25)
-----------------------------

- Support new error syntax reporting (from Robot Framework 4.0)
- Support for browsing workspace symbols (`Ctrl+T`)

New in 0.5.0 (2020-10-26)
-----------------------------

- Support new libdoc format (from Robot Framework 4.0)

New in 0.4.3 (2020-10-12)
-----------------------------

- Updated icon


New in 0.4.2 (2020-09-29)
-----------------------------

- insertText attribute value is now also assigned for CompletionItem. [#158](https://github.com/robocorp/robotframework-lsp/issues/158)
- The environment for an interpreter contributed by some extension is properly used. [#159](https://github.com/robocorp/robotframework-lsp/issues/159)


New in 0.4.1 (2020-09-28)
-----------------------------

- Fixed startup concurrency issue setting up plugin dir contributed by other extensions. [#155](https://github.com/robocorp/robotframework-lsp/issues/155)


New in 0.4.0 (2020-09-22)
-----------------------------

- Default parameters are no longer shown by default in code-completion. [#138](https://github.com/robocorp/robotframework-lsp/issues/138)
- Code completion for individual Keyword arguments is now available. [#107](https://github.com/robocorp/robotframework-lsp/issues/107)
- Signature help is now available for keyword calls (i.e.: textDocument/signatureHelp) -- activated through `Ctrl+Shift+Space` in VSCode. [#139](https://github.com/robocorp/robotframework-lsp/issues/139)
- Importing a python library with capital letters now works. [#143](https://github.com/robocorp/robotframework-lsp/issues/143)
- Verify whitespace changes in the libspec attribute format. [#150](https://github.com/robocorp/robotframework-lsp/issues/150)
- Renamed from robocorptech to robocorp as the publisher on the VSCode Marketplace. [#137](https://github.com/robocorp/robotframework-lsp/issues/137)
- All requests (except document-change related requests) are now asynchronous. [#141](https://github.com/robocorp/robotframework-lsp/issues/141)
- It's now possible to cancel a request in the language server. [#140](https://github.com/robocorp/robotframework-lsp/issues/140)


New in 0.3.2 (2020-09-02)
-----------------------------

- Support for plugins to allow other extensions to hook different python interpreters for different files.
- Provided --version option to command line to just print the version and exit. [#131](https://github.com/robocorp/robotframework-lsp/issues/131)
- Fix handling changes in folders tracked in a workspace.


New in 0.3.1 (2020-07-27)
-----------------------------

- Debugger: support for evaluate request. [#82](https://github.com/robocorp/robotframework-lsp/issues/82)
- Debugger: builtin variables have their own group. [#106](https://github.com/robocorp/robotframework-lsp/issues/106)
- Python 2 support dropped (Python 3.7+ is now required). [#119](https://github.com/robocorp/robotframework-lsp/issues/119)
- Fixed issue normalizing a name according to Robot Framework rules (so that definition is properly found). [#121](https://github.com/robocorp/robotframework-lsp/issues/121)


New in 0.3.0 (2020-07-01)
-----------------------------

- Go to definition for variables.
- Code completion for `Resource Imports` and `Library Imports`.
- Go to definition support for `Resource Imports` and `Library Imports`.
- Do code analysis in a separate process (i.e.: code-completion should not wait for code analysis).
- Create cached document from filesystem (i.e.: ast is not recreated unless `.robot` file is changed).
- Check spaces and unicode characters on pythonpath/resources/imports.
- Config link in the vs code extension documentation is broken.


New in 0.2.3 (2020-06-16)
-----------------------------

- Variables: Code-completion for builtin variables.
- When a user library (.py) changes the related auto-generated spec is automatically updated.
- If `robot.python.executable` is set, it's used to launch the debugger.
- Debugger: step return implementation added.
- Properly Search for python and python3 on the PATH on Linux and Mac.


New in 0.2.2 (2020-06-09)
-----------------------------

- `robot.pythonpath` setting automatically passed as `--pythonpath` argument when launching.
- `robot.pythonpath` setting now used to locate resources and libraries for when resolving keywords. [#79](https://github.com/robocorp/robotframework-lsp/issues/79)
- `robot.variables` setting automatically passed as `--variable` argument when launching. 
- `robot.variables` setting is now used in code completion for variables. [#21](https://github.com/robocorp/robotframework-lsp/issues/21)
- Arguments shown in code completion when creating a Keyword. [#21](https://github.com/robocorp/robotframework-lsp/issues/21)
- Support for Library Import with `WITH NAME` syntax. [#64](https://github.com/robocorp/robotframework-lsp/issues/64)
- Typing info removed when completing keywords. [#89](https://github.com/robocorp/robotframework-lsp/issues/89)


New in 0.2.1 (2020-06-04)
-----------------------------

Critical bugfix to support the debugger with Setup/Teardown. [#85](https://github.com/robocorp/robotframework-lsp/issues/85)


New in 0.2.0 (2020-06-03)
-----------------------------

- Preliminary support for debugging. [#30](https://github.com/robocorp/robotframework-lsp/issues/30)
    - Note: this is an initial release for the feature and should be considered beta (please test and report any issues found).
    - The current functionalities include:
        - Add line breakpoints
        - Pause at breakpoints to inspect the stack and see variables
        - Step in
        - Step over
        - Continue
- Handling `text` only parameter in `textDocument/didChange`. [#78](https://github.com/robocorp/robotframework-lsp/issues/78)
- Updated VSCode client dependency versions. [#65](https://github.com/robocorp/robotframework-lsp/issues/65)
- Snippets code-completion for some constructs (`For In`, `Run Keyword If`). [#69](https://github.com/robocorp/robotframework-lsp/issues/69)


New in 0.1.1 (2020-05-11)
-----------------------------

- Variables code completion is provided for variables assigned to keyword return values. [#21](https://github.com/robocorp/robotframework-lsp/issues/21)
- Variables properly tokenized when completing for variables. [#21](https://github.com/robocorp/robotframework-lsp/issues/21)
- Show argument names in code completion. Fixes [#53](https://github.com/robocorp/robotframework-lsp/issues/53)
- No longer giving error if specified resource points to a directory. Fixes [#63](https://github.com/robocorp/robotframework-lsp/issues/63)
- `tab` now properly applies completions. [#52](https://github.com/robocorp/robotframework-lsp/issues/52)


New in 0.1.0 (2020-05-05)
-----------------------------

- Preliminary code completion support for variables defined in [Variable Tables](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#variable-table).
- Support for keywords defined with a library prefix  [#58](https://github.com/robocorp/robotframework-lsp/issues/58).
- Support for keywords with embededd arguments  [#59](https://github.com/robocorp/robotframework-lsp/issues/59).
- Support for keywords with Gherkin syntax (i.e.: given, when, then, etc) [#59](https://github.com/robocorp/robotframework-lsp/issues/59).


New in 0.0.10 (2020-04-28)
-----------------------------

- Code analysis: check if keywords are properly imported/defined (new in 0.0.10).
- Properly consider that keywords may appear in fixtures and templates (code analysis, code completion and go to definition).
- Add `args` placeholder to Robot launch configuration file (launching).
- Arguments are now shown in keyword documentation (code completion).
- Properly deal with path based library imports (code analysis, code completion and go to definition).


New in 0.0.9 (2020-04-20)
-----------------------------

- Go to definition implemented for keywords.
- Only environment variables set by the user when launching are passed when launching in integrated terminal.
- `~` is properly expanded when it's specified in the logging file.


New in 0.0.8 (2020-04-14)
-----------------------------

- Launch robotframework directly from VSCode (note: right now debugging is still not supported 
  -- a debug run will do a regular launch). Fixes [#29](https://github.com/robocorp/robotframework-lsp/issues/29)
- A setting to complete section headers only in the plural/singular form is now available (`robot.completions.section_headers.form`). Fixes [#42](https://github.com/robocorp/robotframework-lsp/issues/42)
- Improvements in syntax highlighting


New in 0.0.7 (2020-04-04)
-----------------------------

- Return empty list when code formatter has no changes. Fixes [#35](https://github.com/robocorp/robotframework-lsp/issues/35)
- Don't show keywords twice. Fixes [#34](https://github.com/robocorp/robotframework-lsp/issues/34)
- Improvements in syntax highlighting


New in 0.0.6 (2020-04-02)
-----------------------------

- Provide source code formatting with the Tidy builtin tool. Fixes [#26](https://github.com/robocorp/robotframework-lsp/issues/26)
- Fix for incomplete json message ([#33](https://github.com/robocorp/robotframework-lsp/issues/33)) and parsing of .resource ([#32](https://github.com/robocorp/robotframework-lsp/issues/32))


New in 0.0.5 (2020-03-30)
-----------------------------

- Add icon to extension. Fixes [#22](https://github.com/robocorp/robotframework-lsp/issues/22)
- Code completion for keywords.
- License is now Apache 2.0. Fixes [#24](https://github.com/robocorp/robotframework-lsp/issues/24)


New in 0.0.4 (2020-03-05)
-----------------------------

- Code completion for section internal names


New in 0.0.3 (2020-02-11)
-----------------------------

- Code completion for section headers


New in 0.0.2 (2020-02-09)
-----------------------------

- Various internal improvementss


New in 0.0.1 (2020-01-31)
-----------------------------

- Basic syntax highlighting
- Syntax validation