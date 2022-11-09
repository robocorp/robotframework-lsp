New in 1.5.0 (2022-11-09)
-----------------------------

### Bugfixes

- Fixed caching issue where adding a file would not invalidate an internal cache which could make resolved imports appear as unresolved.


New in 1.4.0 (2022-11-02)
-----------------------------

### Bugfixes

- Minor fixes


New in 1.3.5 (2022-10-19)
-----------------------------

### Bugfixes

- If a user is paused in a log message break he should still be able to evaluate keywords based on the previous stack context.
- Fixed internal issue in debugger where a `path` variable could be accessed when undefined.


New in 1.3.0 (2022-10-06)
-----------------------------

### New features

- Vendored Robocop updated to 2.5.0.
- Vendored Robotidy updated to 3.2.0.


New in 1.2.0 (2022-09-28)
-----------------------------

### New features

- Tests may be run/debug using action in gutter (patch by `@jsmzr`).


### Bugfixes

- Fix invalid range in go to definition if range becomes invalid during the go to definition action. [#769](https://github.com/robocorp/robotframework-lsp/issues/769)


New in 1.1.3 (2022-09-14)
-----------------------------

### Bugfixes

- Snippets take into account the value of `robot.completions.keywords.argumentsSeparator`. [#723](https://github.com/robocorp/robotframework-lsp/issues/723)
- Completions properly presented for `Variables` under `*** Settings ***`. [#744](https://github.com/robocorp/robotframework-lsp/issues/744)


New in 1.1.0 (2022-08-24)
-----------------------------

### New features

- [Intellij] When pressing space a completion is no longer applied automatically.
- [Intellij] The plugin will re-register file associations to `.resource` and `.robot`. [#605](https://github.com/robocorp/robotframework-lsp/issues/605)
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

### Bugfixes

- [Intellij] Fixed `NullPointerException` on hover. [#731](https://github.com/robocorp/robotframework-lsp/issues/731)
- [Intellij] `$Prompt$` macro properly replaced when launching. [#737](https://github.com/robocorp/robotframework-lsp/issues/737)
- Operations no longer timeout, rather, they just print to the log (as the timeouts weren't always ideal for slower machines). [#733](https://github.com/robocorp/robotframework-lsp/issues/733)
- Fixed issue where references wouldn't be found properly.
- Variables imported from module folder (`module/__init__.py`) are properly recognized. [#734](https://github.com/robocorp/robotframework-lsp/issues/734) 


New in 1.0.0 (2022-08-09)
-----------------------------

### New features

- Support for PyCharm 22.2
- When a keyword call would resolve to more than one keyword definition with the same name an error is reported. [#432](https://github.com/robocorp/robotframework-lsp/issues/432)
- Note: it can be disabled with `"robot.lint.keywordResolvesToMultipleKeywords": false`.
- If a resource/library/variable import is not found and its name has variables, the resolved name is shown.

### Bugfixes

- If the stop button is pressed in a launch, subprocesses are killed regardless of the value of `RFLS_KILL_ZOMBIE_PROCESSES`.
- The default value (which may resolve to a variable) is considered when resolving environment variables. [#715](https://github.com/robocorp/robotframework-lsp/issues/715)
- File system notifications properly track changes to `.yaml` files.[#710](https://github.com/robocorp/robotframework-lsp/issues/710)
- File system notifications properly handle tracking conflicts when a folder is tracked more than once recursively and not recursively in the same subtree. [#710](https://github.com/robocorp/robotframework-lsp/issues/710)
- Variables are properly resolved recursively. [#715](https://github.com/robocorp/robotframework-lsp/issues/715)
- Doc highlight no longer raises error with unclosed variable.
- A library is no longer considered more than once when collecting keywords.


New in 0.49.0 (2022-07-20)
-----------------------------

- [Intellij] Support for CommonMark and not just plain Markdown.
- [Intellij] Provide hover docs even if definition cannot be found.
- Zombie processes are no longer automatically killed after doing a Robot Framework launch. [#358](https://github.com/robocorp/robotframework-lsp/issues/358)
  - It's possible to enable the previous behavior by setting an environment variable such as: `RFLS_KILL_ZOMBIE_PROCESSES=1`.
- Fix issue where replacement offset in section completion was wrong. [#700](https://github.com/robocorp/robotframework-lsp/issues/700)
- Properly consider extended part of variables in expressions (fixes issue which could make variable not be resolved). [#702](https://github.com/robocorp/robotframework-lsp/issues/702)
- Resolve variable files imported as modules. [#699](https://github.com/robocorp/robotframework-lsp/issues/699)
- Vendored Robocop upgraded to 2.2.0. [#703](https://github.com/robocorp/robotframework-lsp/issues/703)
- Robocop is always run with the project root as the cwd. [#703](https://github.com/robocorp/robotframework-lsp/issues/703)
- By default Failures/Errors inside a TRY..EXCEPT statement won't suspend execution while debugging. [#698](https://github.com/robocorp/robotframework-lsp/issues/698)
- Variables are loaded from classes in Python files. [#704](https://github.com/robocorp/robotframework-lsp/issues/704)
- Fixes to support Robot Framework 5.1:
  - Deal with `robot.running.builder.testsettings.TestDefaults` renamed to `robot.running.builder.settings.Defaults`.
  - Consider new `TASK_HEADER` in AST.
  - Consider that `KeywordCall` is given instead of `EmptyLine` in invalid assign in keyword.


New in 0.48.2 (2022-06-07)
-----------------------------

- New setting `"robot.completions.keywords.argumentsSeparator"` allows customizing spacing betwen keyword and arguments when auto-completing Keyword with arguments. [#683](https://github.com/robocorp/robotframework-lsp/issues/683)


New in 0.48.0 (2022-05-30)
-----------------------------

- Consider as defined a reference to any variable set as a global variable anywhere on the workspace. [#641](https://github.com/robocorp/robotframework-lsp/issues/641)
- Code analysis for template arguments.
- Arguments aren't added when applying completions for keywords in `[Template]`.
- Fixed integration with `robotframework-tidy` which could make formatting the same code a second time misbehave. [#687](https://github.com/robocorp/robotframework-lsp/issues/687)
- Properly consider that `For each input work item` from `rpaframework` receives a keyword as the first parameter. [#684](https://github.com/robocorp/robotframework-lsp/issues/684)
- Added support for `Import Library` keyword. [#675](https://github.com/robocorp/robotframework-lsp/issues/675)
- Properly support constructs with nested usage of `Run Keyword` inside `Run Keyword`. [#686](https://github.com/robocorp/robotframework-lsp/issues/686)
- Updated `robotframework-tidy` to `2.2.0`.
- Updated `Robocop` to `2.0.2`.


New in 0.47.2 (2022-05-11)
-----------------------------

- Fix issue where a reference could be reported more than once.


New in 0.47.0 (2022-05-11)
-----------------------------

- [Intellij] Launch exit info added to console UI in the UI thread. [#662](https://github.com/robocorp/robotframework-lsp/issues/662)
- Properly deal with arguments containing regexp matches.
- Environment variables set using `Set Environment Variable` are now recognized.
- Fix issue where variable with a set literal wasn't properly recognized.
- If an argument is specified multiple times a better error message is shown.
- Fix false positive when argument names are specified with variable names in it.
- Consider that an argument default values may be based on a previous argument. [#664](https://github.com/robocorp/robotframework-lsp/issues/664)
- Properly consider local/global context when dealing with variables.
- Properly recognize loop variables in RF 3. [#661](https://github.com/robocorp/robotframework-lsp/issues/661)
- Properly recognize variable that evaluates to 0.
- Properly recognize variables from Python that start with `DICT__` or `LIST__`.
- Fix syntax highlight of inline python evaluation inside of variables in IF statements. [#666](https://github.com/robocorp/robotframework-lsp/issues/666) 
- Properly consider that the `Comment` keyword arguments should be handled as comments. [#665](https://github.com/robocorp/robotframework-lsp/issues/665)


New in 0.46.0 (2022-04-19)
-----------------------------

- [Intellij] Support Intellij 221. [#652](https://github.com/robocorp/robotframework-lsp/issues/652)
- [Intellij] Consider that getting the preferences may throw a ProcessCanceledException.
- Fix position of variable loaded in SetVariable methods to the var name position and not delimiter start.
- If a variable is defined after its usage inside a keyword it's properly marked as undefined.
- Variables in short format in Set XXX Variable keywords are accepted.
- Variables are properly collected from inline if.
- Variables in Evaluate are properly collected.
- Variables from expressions in conditions are properly collected.


New in 0.45.2 (2022-04-14)
-----------------------------

- Bugfix release handling `Wait Until Keyword Succeeds` properly. [#650](https://github.com/robocorp/robotframework-lsp/issues/650)


New in 0.45.0 (2022-04-13)
-----------------------------

- Fixed issue which could make autocomplete delete code (only in Intellij). [#484](https://github.com/robocorp/robotframework-lsp/issues/484)
- Handle `Run Keywords` properly. [#642](https://github.com/robocorp/robotframework-lsp/issues/642)
- Proper semantic highlighting for `ELSE/ELSE IF` in `Run Keyword If`.
- Proper semantic highlighting for `AND` in `Run Keywords`.
- Hover over arguments from `Run Keyword` targets works properly.
- Properly mark tests passed/failed in test view with `Robot Framework 3.x`. [#644](https://github.com/robocorp/robotframework-lsp/issues/644)
- Fix to `robotframework-tidy` to no longer convert `*Tasks*` to `*Test Cases*`.
- Fix issue in semantic highlighting when a slash was encountered. [#647](https://github.com/robocorp/robotframework-lsp/issues/647)
 

New in 0.44.0 (2022-04-07)
-----------------------------

- Improvements dealing with **Variables**:
  - Variables in document are considered in Libdoc arguments. [#634](https://github.com/robocorp/robotframework-lsp/issues/634) 
  - Escaping rules are considered when setting variables using `Set Variable XXX` keywords. [#638](https://github.com/robocorp/robotframework-lsp/issues/638) 
  - Variables set with `Set Local Variable` are recognized. [#637](https://github.com/robocorp/robotframework-lsp/issues/637) 
  - Consider that loading an environment variable may have a default value. [#633](https://github.com/robocorp/robotframework-lsp/issues/633) 
  - Variables in python files with annotated assignments are supported (i.e.: `value: int = 10`). [#629](https://github.com/robocorp/robotframework-lsp/issues/629)
  - Variables in templates are not reported as errors. [#632](https://github.com/robocorp/robotframework-lsp/issues/632)
  - Properly deal with variables with other variables inside. [#631](https://github.com/robocorp/robotframework-lsp/issues/631)
  - Load variables from python module with `get_variables` returning a literal dict. [#639](https://github.com/robocorp/robotframework-lsp/issues/639)
- Improvements in debugger:
  - The debugger no longer stops in `Run Keyword And Return Status` by default. [#625](https://github.com/robocorp/robotframework-lsp/issues/625)
  - Assign to variable in debug console repl (i.e.: `${lst}=    Create list    a    b`).
  - Fixed case where breakpoints in `.py` files wouldn't be added. 
- Upgraded vendored `robocop` to `2.0.1`. 
- Upgraded vendored `robotframework-tidy` to `2.1.0`. 


New in 0.43.2 (2022-03-29)
-----------------------------

- Additional fix in cache invalidation for dependencies. [#617](https://github.com/robocorp/robotframework-lsp/issues/617)


New in 0.43.0 (2022-03-28)
-----------------------------

- Improvements dealing with **Variables**:
    - Undefined variables are now reported. [#334](https://github.com/robocorp/robotframework-lsp/issues/334)
        - `robot.variables`: may be used to specify variables used for launching as well as code-completion/code analysis.
        - `robot.lint.ignoreVariables`: may be used to set variables to be ignored in linting.
        - `robot.loadVariablesFromArgumentsFile` may be used to load variables from an arguments file for code-completion and code analysis.
            - Note: the arguments file still needs to be separately set during launching too.
        - Variables are recognized in expressions as well as inner variables.
    - Variables set with the following keywords are recognized: [#577](https://github.com/robocorp/robotframework-lsp/issues/577)
        - Set Task Variable
        - Set Test Variable
        - Set Suite Variable
        - Set Global Variable
    - Variable files with a `.yml` are properly recognized (previously only `.yaml` was supported). 
    - Semantic highlighting properly deals with advanced variable syntax (with variables inside variables or using a subscript).
    - Variables in assign now have the same color as variables in other places. [#613](https://github.com/robocorp/robotframework-lsp/issues/613)
    - Variable imports which can't be resolved are reported.
        - May be disabled with `robot.lint.undefinedVariableImports`.
- Fix issue in cache invalidation for dependencies. [#617](https://github.com/robocorp/robotframework-lsp/issues/617)
- `\\` is escaped to `\` when passed in the library arguments. [#608](https://github.com/robocorp/robotframework-lsp/issues/608)
- Fix in heuristics to match arguments which could result in wrong argument analysis in keyword calls. [#603](https://github.com/robocorp/robotframework-lsp/issues/603)
- Hover now provides custom hints for variables, imports and parameters.


New in 0.42.0 (2022-03-14)
-----------------------------

- Semantic highlighting supports Gherkin style (`Given`, `Then`, ...). [#581](https://github.com/robocorp/robotframework-lsp/issues/581) (patch by @weltings)
- Semantic highlighting only highlights names up to a dot if a related import/resource is found to avoid conflict with Keywords with a dot in the name. [#585](https://github.com/robocorp/robotframework-lsp/issues/585) (patch by @weltings)
- Semantic highlighting available for variables in keyword calls. [#586](https://github.com/robocorp/robotframework-lsp/issues/586)
- Semantic highlighting for `WHILE limit=` and `EXCEPT type=`.
- Report unresolved variables when resolving a resource/import. [#600](https://github.com/robocorp/robotframework-lsp/issues/600) 
- Performance improvements
  - Don't index everything in AST when only items from the section (LibraryImport, ResourceImport, ...) are requested.
  - Caching of dependencies.
- `Run Keyword If` is now properly handled across all features in the language server. [#495](https://github.com/robocorp/robotframework-lsp/issues/495)
- `None` is no longer reported as undefined keyword when used as keyword call. [#597](https://github.com/robocorp/robotframework-lsp/issues/597)
- Misleading message saying that RF is old when it's not installed is no longer shown.


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