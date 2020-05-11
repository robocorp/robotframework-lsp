[Language Server Protocol](https://github.com/Microsoft/language-server-protocol) implementation for [Robot Framework](https://robotframework.org/)
=============

Requirements
-------------

Python 3.7+ and [Robot Framework](https://robotframework.org/) 3.2+ (note that [Robot Framework](https://robotframework.org/) may
be installed in a separate python interpreter in case you need to run it with an older version of Python).


Installing
-----------

`robotframework-lsp` can be installed from the [VisualStudio Marketplace](https://marketplace.visualstudio.com/items?itemName=robocorptech.robotframework-lsp) or as a `.vsix`.

To get a `.vsix`, download the latest `Deploy Extension` in [Robotframework-lsp Github Actions](https://github.com/robocorp/robotframework-lsp/actions?query=workflow%3A%22Deploy+Extension%22).

See: [Install from a vsix](https://code.visualstudio.com/docs/editor/extension-gallery#_install-from-a-vsix) for details installing a `.vsix` into VSCode.

See: [Getting Started](https://hub.robocorp.com/development/best-practices/language-server-protocol-for-robot-framework/) for a tutorial with some screenshots.


Configuration
-------------

After having `robotframework-lsp` installed, some configurations (such as specifying
the python executable used for launching the Language Server or Robot Framework)
may be needed.

See: [Config](docs/config.md) for details.
  

Features (0.1.1)
-----------------

- Preliminary code completion support for variables defined in [Variable Tables](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#variable-table) and [Keyword Return Values](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#return-values-from-keywords) (new in 0.1.1).
- Code analysis: check if keywords are properly imported/defined.
- Code completion for keywords, section headers and section settings.
- Go to definition for keywords.
- Launch `.robot` files.
- Syntax highlighting.
- Syntax validation.
- Code Formatting (see: [Editor Settings](https://code.visualstudio.com/docs/getstarted/settings#_language-specific-editor-settings) for details on how to toggle code formatting just for `robotframework`).

See: [Changelog](docs/changelog.md) for details.


Developing
------------

See: [Developing](docs/develop.md) for details on how to develop `robotframework-lsp` itself.

License: Apache 2.0
-------------------
