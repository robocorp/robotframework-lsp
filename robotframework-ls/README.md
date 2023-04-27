# [Language Server Protocol](https://github.com/Microsoft/language-server-protocol) implementation for [Robot Framework](https://robotframework.org/)

## Requirements

Python 3.7+ and [Robot Framework](https://robotframework.org/) 3.2+.

Note: if using the [Robot Framework Selenium Library](https://github.com/robotframework/SeleniumLibrary), version 4.4+ is required.

## Installing

`Robot Framework Language Server` can be installed from the [VisualStudio Marketplace](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp) or as a `.vsix`.

To get a `.vsix`, download the latest `Deploy - RobotFramework Language Server Extension` in [Robotframework-lsp Github Actions](https://github.com/robocorp/robotframework-lsp/actions?query=workflow%3A%22Deploy+-+RobotFramework+Language+Server+Extension%22).

See: [Install from a vsix](https://code.visualstudio.com/docs/editor/extension-gallery#_install-from-a-vsix) for details installing a `.vsix` into VSCode.

See: [Getting Started](https://robocorp.com/docs/developer-tools/visual-studio-code/lsp-extension#what-is-the-language-server-protocol-lsp-and-why-is-it-useful) for a tutorial with some screenshots.

## Configuration

After having `Robot Framework Language Server` installed, some configurations (such as specifying
the python executable used for launching the Language Server or Robot Framework)
may be needed.

See: [Config](docs/config.md) for details.

See: [FAQ](docs/faq.md) for common issues encountered while configuring the language server.

## Contributing

See: [Contributing](docs/contributing.md) for how to help in the development of `Robot Framework Language Server`.

## Reporting Issues

See: [Reporting Issue](docs/reporting_issues.md) for details on how to report some issue in the `Robot Framework Language Server`.

## Features (1.10.1)

-   Robot Output View:
    -   View current task/test being executed.
    -   Shows Keyword being executed in real time.
-   Robot Documentation View:
    -   Select a library import for the full library documentation.
    -   Select another element for its docstring.
-   Test Explorer support in VSCode.
-   Interactive Console: a REPL for interactively experimenting with Robot Framework (for VSCode).
-   Code analysis:
    -   Keywords/variables.
    -   Keyword arguments.
-   Linting with [Robocop](https://robocop.readthedocs.io/en/latest/).
-   Code completion:
    -   Keywords, variables, sections and snippets.
    -   Auto imports from keywords in the workspace.
-   Go to definition:
    - Keywords, variables and imports.
-   Find references for keywords and variables.
-   Refactoring:
    -   Rename keywords.
    -   Rename variables.
    -   Extract local variable.
    -   Extract variable to variables section.
-   Quick fixes (VSCode: `Ctrl + .`):
    -   Add import for unresolved keyword.
    -   Create local variable for unresolved variable.
    -   Create argument for unresolved variable.
    -   Creat variable in variables section for unresolved variable.
    -   Assign keyword to variable.
    -   Surround with Try..Except.
-   Symbols browser for keywords in workspace (VSCode: `Ctrl + T`).
-   Document symbols (VSCode: `Ctrl + Shift + O`).
-   Highlight of keywords and variables.
-   Syntax highlighting (using `semanticTokens`).
-   Syntax validation.
-   Signature Help (VSCode: `Ctrl + Shift + Space`).
-   Code Formatting (see: [Editor Settings](https://code.visualstudio.com/docs/getstarted/settings#_language-specific-editor-settings) for details on how to toggle code formatting just for `robotframework`).
-   Hover.
-   Code folding.
-   Launch `.robot` files.
-   Debugger:
    -   Add line breakpoints in `.robot` or `.py` files
    -   Break on log error/failure
    -   Evaluate keywords in debug console/hover/watch
    -   Pause at breakpoints to inspect the stack and see variables
    -   Breakpoint condition/hitCondition/logMessage
    -   Step in
    -   Step over
    -   Step return
    -   Continue

See: [Changelog](docs/changelog.md) for details.

## License: Apache 2.0
