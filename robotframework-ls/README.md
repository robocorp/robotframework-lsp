[Language Server Protocol](https://github.com/Microsoft/language-server-protocol) implementation for [Robot Framework](https://robotframework.org/)
=============

Requirements
-------------

Python 3.7+ and [Robot Framework](https://robotframework.org/) 3.2+.

Note: if using the [Robot Framework Selenium Library](https://github.com/robotframework/SeleniumLibrary), version 4.4+ is required.

Installing
-----------

`Robot Framework Language Server` can be installed from the [VisualStudio Marketplace](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp) or as a `.vsix`.

To get a `.vsix`, download the latest `Deploy - RobotFramework Language Server Extension` in [Robotframework-lsp Github Actions](https://github.com/robocorp/robotframework-lsp/actions?query=workflow%3A%22Deploy+-+RobotFramework+Language+Server+Extension%22).

See: [Install from a vsix](https://code.visualstudio.com/docs/editor/extension-gallery#_install-from-a-vsix) for details installing a `.vsix` into VSCode.

See: [Getting Started](https://robocorp.com/docs/developer-tools/visual-studio-code/lsp-extension#what-is-the-language-server-protocol-lsp-and-why-is-it-useful) for a tutorial with some screenshots.


Configuration
-------------

After having `Robot Framework Language Server` installed, some configurations (such as specifying
the python executable used for launching the Language Server or Robot Framework)
may be needed.

See: [Config](docs/config.md) for details.

See: [FAQ](docs/faq.md) for common issues encountered while configuring the language server.

  
Contributing
--------------

See: [Contributing](docs/contributing.md) for how to help in the development of `Robot Framework Language Server`.


Reporting Issues
-----------------

See: [Reporting Issue](docs/reporting_issues.md) for details on how to report some issue in the `Robot Framework Language Server`.


Features (1.5.0)
-----------------

- Robot Output View (shows output details for the current output.xml -- note: currently in beta). 
- Robot Documentation View (shows documentation for the current editor selection).
- Test Explorer support in VSCode.
- Interactive Console: a REPL for interactively experimenting with Robot Framework (for VSCode).
- Code analysis: checks if keywords/variables are properly imported/defined.
- Linting with [Robocop](https://robocop.readthedocs.io/en/latest/).
- Code completion for keywords, keyword parameters, section headers, section settings, variables, resource imports and library imports.
- Code completion for all keywords in the workspace with auto-import of Library or Resource.
- Casing of keywords from libraries used in code-completion can be configured.
- Go to definition for keywords, variables, resource imports and library imports.
- Find references for keywords and variables.
- Rename keywords and variables.
- Symbols browser for keywords in workspace (activated through `Ctrl + T`).
- Document symbols.
- Highlight of keywords and variables.
- Syntax highlighting (using `semanticTokens`).
- Syntax validation.
- Signature Help (activated through `Ctrl + Shift + Space`).
- Code Formatting (see: [Editor Settings](https://code.visualstudio.com/docs/getstarted/settings#_language-specific-editor-settings) for details on how to toggle code formatting just for `robotframework`).
- Hover.
- Code folding.
- Launch `.robot` files.
- Debugger:
  - Add line breakpoints in `.robot` or `.py` files
  - Break on log error/failure
  - Evaluate keywords in debug console/hover/watch
  - Pause at breakpoints to inspect the stack and see variables
  - Breakpoint condition/hitCondition/logMessage
  - Step in
  - Step over
  - Step return
  - Continue

See: [Changelog](docs/changelog.md) for details.



License: Apache 2.0
-------------------
