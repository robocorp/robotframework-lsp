New in 0.41.0 (2022-02-22)
-----------------------------

- Argument analysis is now also done for `Run Keyword` variants. [#572](https://github.com/robocorp/robotframework-lsp/issues/572)
- [Debugger] It's now possible to ignore failures inside some keywords so that the debugger doesn't break in these cases when `Robot Log FAIL` is enabled. [#575](https://github.com/robocorp/robotframework-lsp/issues/575)
  - Customizable through the `RFLS_IGNORE_FAILURES_IN_KEYWORDS` and `RFLS_IGNORE_FAILURES_IN_KEYWORDS_OVERRIDE` environment variables (see [Config](https://github.com/robocorp/robotframework-lsp/blob/master/robotframework-ls/docs/config.md#environment-variables) for details).
- Performance improvements
  - Improved AST indexing.
  - Notification that settings changed are only sent to the server api if they actually changed.
  - Documentation is now lazily loaded during code-completion.
- References are found when find references is activated from the keyword definition. [#576](https://github.com/robocorp/robotframework-lsp/issues/576)
- Semantic highlighting for Keywords with dotted access improved.
- The documentation conversion from `REST` and `ROBOT` to `markdown` is now done internally. 


New in 0.40.1 (2022-02-12)
-----------------------------

- Critical fix: skip analysis of arguments for `Run Keyword` variants.


New in 0.40.0 (2022-02-12)
-----------------------------

- Keyword calls and library inits are now validated according to the signature. [#558](https://github.com/robocorp/robotframework-lsp/issues/558)
- Usage of deprecated keywords is marked with a strikethrough.
- When a libspec can't be generated the reason and possible fixes are properly shown to the user.
- Signature info is now shown for libraries.
- Added options related to enabling/disabling linting features individually (see: `robot.lint.*` settings).
- Added `${EMPTY}` completion. [#566](https://github.com/robocorp/robotframework-lsp/issues/566)
- Snippet completions are now done at the target `robot.python.executable` and not `robot.language-server.python` (to account for statements only available depending on robot version).
- The active parameter is properly highlighted in the signature help.
- The signature help is shown whenever a space is typed.
- Fixed case where `try..finally` wasn't stepping properly with step next.
- When debugging variable values are shown on hover. [#550](https://github.com/robocorp/robotframework-lsp/issues/550)
- A better error message is provided in the case where `robot` is not available or shadowed. [#563](https://github.com/robocorp/robotframework-lsp/issues/563)
- Semantic highlighting is provided for variables in documentation. [#564](https://github.com/robocorp/robotframework-lsp/issues/564)
- The current argument is highlighted during hover.


New in 0.39.1 (2022-02-07)
-----------------------------

- Critical fix: properly apply new colors during semantic highlighting in Intellij. [#565](https://github.com/robocorp/robotframework-lsp/issues/565)


New in 0.39.0 (2022-02-03)
-----------------------------

- Robot Framework 5 is now officially supported.
  - New statements (TRY, WHILE) should now work for all existing features.
- Debugger: step next considers that control flow statements are a part of the current keyword.
- Debugger: Fixed issue initializing `pydevd` debugger when it's already present in the environment. [#556](https://github.com/robocorp/robotframework-lsp/issues/556)
- Semantic highlighting properly colors keyword calls with a namespace in fixtures. [#533](https://github.com/robocorp/robotframework-lsp/issues/533)
- Libraries without keywords (a.k.a `DataDriver`) are no longer considered undefined. [#559](https://github.com/robocorp/robotframework-lsp/issues/559)
- Properly deal with suites with a `__` prefix when launching. [#561](https://github.com/robocorp/robotframework-lsp/issues/561)
- Raised time to obtain libspec mutex and give a better message on failure. [#555](https://github.com/robocorp/robotframework-lsp/issues/555)


New in 0.38.1 (2022-01-27)
-----------------------------

- Minors


New in 0.38.0 (2022-01-26)
-----------------------------

- [Intellij] Variables configured in robot.variables are properly passed to launched process. [#548](https://github.com/robocorp/robotframework-lsp/issues/548)
- It's now possible to break when an error or failure is logged with the following environment variables:
  - `RFLS_BREAK_ON_FAILURE=1`
  - `RFLS_BREAK_ON_ERROR=1`
- When launching, better heuristics are used to create a proper test suite. [#482](https://github.com/robocorp/robotframework-lsp/issues/482)
  - A suite is created considering __init__.robot in parents based on the specified `target`.
  - By default the `target` will be used to compute the suite as well as the needed filtering.
- MarkupContent is now properly used in the signature help.
- Go to definition now works properly with .yaml files.
- The signature part of a keyword is now bold in the documentation.
- Keyword namespace access now has a different color in semantic highlighting. [#533](https://github.com/robocorp/robotframework-lsp/issues/533)


New in 0.37.0 (2022-01-19)
-----------------------------

- Code analysis will now notify if Library or Resource cannot be resolved. [#542](https://github.com/robocorp/robotframework-lsp/issues/542)
- If Run Keyword has a variable concatenated, it's no longer considered an error. [#534](https://github.com/robocorp/robotframework-lsp/issues/534)
- Properly resolve variables in arguments in the libspec generation. [#535](https://github.com/robocorp/robotframework-lsp/issues/535)
- Improvements related to scheduling the lint after changing the editor.


New in 0.36.0 (2022-01-17)
-----------------------------

- Fixed an issue which could make file system change notifications be ignored.


New in 0.35.0 (2021-12-22)
-----------------------------

- Environment variables are properly passed when launching on Intellij. [#529](https://github.com/robocorp/robotframework-lsp/issues/529)
- On Robot Framework 5, the builtin tidy is no longer available, so, the new robotidy is used automatically.                                  


New in 0.34.0 (2021-12-16)
-----------------------------

- Minors


New in 0.33.0 (2021-12-14)
-----------------------------

- PYTHONPATH entries passed as -P to libdoc are now normalized (fixes issues passing entries which could end with `/.`).


New in 0.32.0 (2021-12-05)
-----------------------------

- Updated Robocop to 1.12.0 and vendored a TOML implementation.
- Marked Intellij plugin as being compatible with Intellij 213.*


New in 0.31.0 (2021-12-01)
-----------------------------

- Minors

New in 0.30.0 (2021-12-01)
-----------------------------

- Library arguments can now be used in the libspec generation. Patch by `Jozef Grajciar`. [#343](https://github.com/robocorp/robotframework-lsp/issues/343) 
  - `robot.libraries.libdoc.needsArgs` setting can be used to specify which libraries require arguments in the generation.
  - `Remote` and `FakerLib` are set by default.
- Libspec files may be pre-generated. [#163](https://github.com/robocorp/robotframework-lsp/issues/163)
  - `robot.libraries.libdoc.preGenerate` may be used to specify which libraries to pre-generate.
  - Some heuristics cover a few libraries which are always pre-generated if installed.
- Fixes related to aliasing libraries. [#397](https://github.com/robocorp/robotframework-lsp/issues/397)
- Documentation is shown for keywords still not imported. [#516](https://github.com/robocorp/robotframework-lsp/issues/516)
- Module is shown for for keywords already imported. [#507](https://github.com/robocorp/robotframework-lsp/issues/507)


New in 0.29.0 (2021-11-16)
-----------------------------

- Fixed error on dictionary completions. [#503](https://github.com/robocorp/robotframework-lsp/issues/503)


New in 0.28.0 (2021-11-08)
-----------------------------

- The code.formatter setting is now properly recognized as a string. [#490](https://github.com/robocorp/robotframework-lsp/issues/490)
- Fixed crash during startup (the timeout expected to startup was too short). [#489](https://github.com/robocorp/robotframework-lsp/issues/489)


New in 0.27.0 (2021-11-01)
-----------------------------

- Minors


New in 0.26.0 (2021-11-01)
-----------------------------

- Consider `PYTHONPATH` when searching for `Resource` imports. [#486](https://github.com/robocorp/robotframework-lsp/issues/486)
- Properly consider that `[Template]` has a Keyword target. [#479](https://github.com/robocorp/robotframework-lsp/issues/479)
- Mark `robot.codeFormatter` as a string and not an array. [#481](https://github.com/robocorp/robotframework-lsp/issues/481)


New in 0.25.0 (2021-10-21)
-----------------------------

- The `robotframework-tidy` code formatter is integrated.
  - Note: `"robot.codeFormatter": "robotidy"` must be set in the settings to use it.
- The `CURDIR` variable is properly resolved. [#449](https://github.com/robocorp/robotframework-lsp/issues/449)
- Bundled `Robocop` updated `1.11.2`.


New in 0.24.0 (2021-10-13)
-----------------------------

- Variable in run keyword argument should not be considered error. [#468](https://github.com/robocorp/robotframework-lsp/issues/468)
- Fixed crash during startup: Improving port collection from Remote FS Observer. [#434](https://github.com/robocorp/robotframework-lsp/issues/434)


New in 0.23.2 (2021-09-22)
-----------------------------

- Fixed issue launching when no environment is provided.


New in 0.23.1 (2021-09-21)
-----------------------------

- Fixed issue specifying files to be tracked in the filesystem observer. [#450](https://github.com/robocorp/robotframework-lsp/issues/450)


New in 0.23.0 (2021-09-20)
-----------------------------

- Minor bugfixes


New in 0.22.0 (2021-09-06)
-----------------------------

- [Intellij] Additional logging to diagnose startup issues.
- Recognize keywords when used as arguments of other keywords (for BuiltIn library). [#291](https://github.com/robocorp/robotframework-lsp/issues/291)


New in 0.21.0 (2021-08-18)
-----------------------------

- [Intellij] Dialog to select Python executable now accepting ~ and variables. [#418](https://github.com/robocorp/robotframework-lsp/issues/418)
- [Intellij] Fix internal issue getting language server communication. [#421](https://github.com/robocorp/robotframework-lsp/issues/421)
- Find definition properly works for dictionary variables. Fix by: Marduk Bolaños. [#407](https://github.com/robocorp/robotframework-lsp/issues/407)
- Complete dictionary items when the variable name includes spaces. Fix by: Marduk Bolaños.


New in 0.20.0 (2021-07-29)
-----------------------------

- [Intellij] Intellij 212 (2021.2) is now supported.
- [Intellij] Properly to go to definition of variables inside of arguments. [#404](https://github.com/robocorp/robotframework-lsp/issues/404)
- ${workspaceFolder} is accepted when resolving variables. 
- ${env:VAR_NAME} is accepted when resolving variables.
- Robocop updated to 1.8.1.
- When using the poll mode for tracking file changes, it's possible to ignore directories. [#398](https://github.com/robocorp/robotframework-lsp/issues/398)
- dict(&)/list(@) variables can be referenced as regular ($) variables. [#387](https://github.com/robocorp/robotframework-lsp/issues/387)
- Completion for dictionary items with subscript. Fix by: Marduk Bolaños. [#301](https://github.com/robocorp/robotframework-lsp/issues/301) 
- Completion for dictionary variable names. Fix by: Marduk Bolaños. [#301](https://github.com/robocorp/robotframework-lsp/issues/301)


New in 0.19.0 (2021-07-14)
-----------------------------

- [Intellij] Bugfixes related to timeouts.


New in 0.18.0 (2021-06-02)
-----------------------------

- Support for variables import:
  - Loads variables from `.py` and `.yaml` files.
- Semantic highlighting: equals sign no longer causes incorrect coloring on `catenate` keyword and `documentation` section.
- A module shadowing `builtin.py` no longer causes the default `Builtin` module not to be found anymore.
- Code analysis no longer throws error when dealing with a `Library` without a name declared. 
- Robocop updated to 1.7.1.
- [Intellij] `${workspace}` and `${env.SOME_VAR}` properly replaced for the language server python executable specified in the settings.


New in 0.17.0 (2021-05-24)
-----------------------------

- Variables may be used in settings. See the [related FAQ](https://github.com/robocorp/robotframework-lsp/blob/master/robotframework-ls/docs/faq.md#how-to-use-variables-in-settings) for details.
- Semantic highlighting was improved to differentiate the parameter (name) from the argument (value).
- Variables are now shown in the structure view.
- When launching a `.robot`, if a `__init__.robot` is present in the same directory, a `--suite` is done by default.
- Breakpoints are properly hit on `__init__.robot` files.
- [Intellij] Fixed exception related to code-folding during initializing.
- Fixed issue which could lead to high-cpu due to filesystem polling.
  - It's now possible to set an environment variable `ROBOTFRAMEWORK_LS_POLL_TIME=<poll time in seconds>` to change the filesystem target poll time.
  - When possible, it's recommended to set an environment variable `ROBOTFRAMEWORK_LS_WATCH_IMPL=watchdog` to use native watches on Linux and MacOS (already default on Windows).
  - A file-observer is started as a separate process and multiple clients communicate with it.
  

New in 0.16.0 (2021-05-12)
-----------------------------

- [Intellij] Outline is shown in the structure view.
- [Intellij] Fixed issue where a cancelled exception was logged.
- It's possible to configure the casing of keywords from libraries used in code-completion.


New in 0.15.0 (2021-05-05)
-----------------------------

- Debugger:
  - Add line breakpoints in `.robot` or `.py` files.
  - Evaluate keywords.
  - Pause at breakpoints to inspect the stack and see variables.
  - Step in.
  - Step over.
  - Step return.
  - Continue.


New in 0.14.0 (2021-04-14)
-----------------------------

- [Intellij] Add code-folding support to Intellij client.
- [Intellij] Wrap the preferences labels at 100 columns. [#307](https://github.com/robocorp/robotframework-lsp/issues/307)
- [Intellij] Handle case where hover info is unavailable. [#306](https://github.com/robocorp/robotframework-lsp/issues/306)
- [Intellij] Consider cases where the position from the LSP is no longer valid. [#297](https://github.com/robocorp/robotframework-lsp/issues/297)
- [Intellij] Protect against NPE on Semantic Highlighting.
- Robocop linter is now opt-in instead of opt-out. [#312](https://github.com/robocorp/robotframework-lsp/issues/312)
- Add code-completion for `${CURDIR}`. [#313](https://github.com/robocorp/robotframework-lsp/issues/313)
- Use listener instead of monkey-patching when debugging (RF 4 onwards). [#310](https://github.com/robocorp/robotframework-lsp/issues/310)
- Silence exception from creating libspec for Dialogs module. [#93](https://github.com/robocorp/robotframework-lsp/issues/93)
- Search `PYTHONPATH` when looking to resolve relative paths in Imports. [#266](https://github.com/robocorp/robotframework-lsp/issues/266)


New in 0.13.1 (2021-04-08)
-----------------------------

- [Intellij] Supporting Intellij 2020.3 to 2021.1.
- [Intellij] Cancel semantic tokens request if document changes.
- [Intellij] Check if range is valid before applying semantic token.
- [Intellij] Add hover support. [#278](https://github.com/robocorp/robotframework-lsp/issues/278)
- [Intellij] updated lsp4j to 0.12.0
- Resolve environment variables when trying to resolve libraries/resources paths (i.e.: `%{env_var}`). [#295](https://github.com/robocorp/robotframework-lsp/issues/295)
- Properly resolve variables for Library imports (not only Resource imports).


New in 0.12.0 (2021-04-01)
-----------------------------

- By default, fsnotify (polling) is now used on Linux and Mac and watchdog (native) on Windows due to resource usage limits on Linux and Mac.
  Using `watchdog` is still recommended when possible. See the [FAQ](https://github.com/robocorp/robotframework-lsp/blob/master/robotframework-ls/docs/faq.md#how-to-change-the-file-watch-mode)
  for details. 
- Code analysis with empty teardown works properly. [#289](https://github.com/robocorp/robotframework-lsp/issues/289)
- No longer recursing on local circular imports. [#269](https://github.com/robocorp/robotframework-lsp/issues/269)
- System directory separator `${/}` is recognized. [#153](https://github.com/robocorp/robotframework-lsp/issues/153)
- It's now possible to enable logging through a `ROBOTFRAMEWORK_LS_LOG_FILE` environment variable.
- [Robocop](https://robocop.readthedocs.io/en/latest/) fixes integrated (trailing blank line, misaligned variable).
- [Intellij] Fixed issue initializing language server with arguments in Mac OS.


New in 0.11.1 (2021-03-29)
-----------------------------

- [Robocop](https://robocop.readthedocs.io/en/latest/) updated to 1.6.1.
- Fixes in semantic syntax hightlighting with Robot Framework 3.x.
- Keywords from `Reserved.py` are no longer shown for auto-import.


New in 0.11.0 (2021-03-24)
-----------------------------

- [Intellij] Improved initialization of language server to validate the python executable and ask for a new one if the one found is not valid.
- [Intellij] Fix PYTHONPATH so that the language server shipped in the Intellij plugin is the one used.
- [Intellij] When requesting a completion, cancel previous one requested.
- [Intellij] Language server executable can be project dependent.
- [Robocop](https://robocop.readthedocs.io/en/latest/) is now used to lint (enabled by default, can be disabled in settings).
- Snippets completion is now properly case-insensitive.
- If there's some problem computing semantic tokens, log it and still return a valid value. [#274](https://github.com/robocorp/robotframework-lsp/issues/274)
- If a keyword name is defined in the context, don't try to create an auto-import for it.
- Reworded some settings to be clearer.


New in 0.10.0 (2021-03-19)
-----------------------------

- Fixed issue initializing the language server if there was a space in the installation path.
- Improved coloring is now computed on a thread using the `semanticTokens/full` request.
- Fixed issue applying `FOR` templates.
- Multi-line completions are properly indented when applied.
- `FOR` templates no longer have a `/` in them.
- Added templates for `IF` statements.


New in 0.9.1 (2021-03-20)
-----------------------------

- Handles .resource files. [#251](https://github.com/robocorp/robotframework-lsp/issues/251)
- If some error happens starting up the language server, show more information.
- The settings may now also be set per project and not only globally. [#254](https://github.com/robocorp/robotframework-lsp/issues/254)
- Fix issue getting prefix for filesystem completions. [#256](https://github.com/robocorp/robotframework-lsp/issues/256)
- Support python packages as libraries (package/__init__.py). [#228](https://github.com/robocorp/robotframework-lsp/issues/228)


New in 0.9.0 (2021-03-03)
-----------------------------

- Fixed issue applying arguments completion.
- Code completion for arguments properly brought up if a part of it is still not typed.
- Prefix properly computed for completions. [#248](https://github.com/robocorp/robotframework-lsp/issues/248)
- Completion with dollar sign properly applied. [#249](https://github.com/robocorp/robotframework-lsp/issues/249)
- Gathering workspace symbols is much faster.
- Keyword completions should not be duplicated by the auto-import Keyword completions anymore. 
- It's now possible to use polling instead of native filesystem notifications
  - It may be useful in case watchdog is having glitches.
  - To use it, set an environment variable: `ROBOTFRAMEWORK_LS_WATCH_IMPL=fsnotify`


New in 0.8.0 (2021-02-16)
-----------------------------

- Properly consuming stderr from the language server process (redirecting it to `${user.home}/.robotframework-ls/.intellij-rf-ls-XXX.log`).
- Notifying when python cannot be found on the PATH.
- Improved language server startup.
- Added syntax highlighting for variables. 


New in 0.7.2 (2021-02-10)
-----------------------------

- Initial version with support for:
  - Settings for the language server may be set at `File > Settings > Languages & Frameworks > Robot Framework Language Server`
  - Code completion
  - Code analysis
  - Go to definition
  - Browse Keywords (symbols)
  - Syntax highlighting (pretty basic right now)