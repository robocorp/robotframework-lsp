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

See: [Getting Started](https://hub.robocorp.com/development/best-practices/language-server-protocol-for-robot-framework/) for a tutorial with some screenshots.


Configuration
-------------

After having `Robot Framework Language Server` installed, some configurations (such as specifying
the python executable used for launching the Language Server or Robot Framework)
may be needed.

See: [Config](docs/config.md) for details.
  

Features (0.6.2)
-----------------

- Code analysis: checks if keywords are properly imported/defined.
- Code completion for keywords, keyword parameters, section headers, section settings, variables, resource imports and library imports.
- Go to definition for keywords, variables, resource imports and library imports
- Symbols browser for keywords (activated through `Ctrl + T`).
- Syntax highlighting.
- Syntax validation.
- Signature Help (activated through `Ctrl + Shift + Space`).
- Code Formatting (see: [Editor Settings](https://code.visualstudio.com/docs/getstarted/settings#_language-specific-editor-settings) for details on how to toggle code formatting just for `robotframework`).
- Launch `.robot` files.
- Debug `.robot` files.
    - Debugger features:
        - Evaluate keywords in debug console/hover/watch
        - Add line breakpoints
        - Pause at breakpoints to inspect the stack and see variables
        - Step in
        - Step over
        - Step return
        - Continue

See: [Changelog](docs/changelog.md) for details.


Developing
------------

See: [Developing](docs/develop.md) for details on how to develop `Robot Framework Language Server`.

Reporting Issues
-----------------

See: [Reporting Issue](docs/reporting_issues.md) for details on how to report some issue in the `Robot Framework Language Server`.

License: Apache 2.0
-------------------
