Robot Framework Language Server for Intellij
=============================================

Requirements
-------------
Intellij (2020.3 onwards) or some other Intellij-based product (such as PyCharm).

Python 3.7+ and [Robot Framework](https://robotframework.org/) 3.2+.

Note: if using the [Robot Framework Selenium Library](https://github.com/robotframework/SeleniumLibrary), version 4.4+ is required.

Important
-----------

The Intellij Language Server integration is currently in alpha for early access.
Please report any issues found during testing.


Installing latest from JetBrains Marketplace
---------------------------------------------

Install the latest from [JetBrains Marketplace](https://plugins.jetbrains.com/plugin/16086-robot-framework-language-server)
from Intellij by accessing `Settings > Plugins` and searching for `Robocorp`.

Installing latest from Github Actions
--------------------------------------

See the [FAQ: How to install a build from GitHub on Intellij?](https://github.com/robocorp/robotframework-lsp/blob/master/robotframework-ls/docs/faq.md#how-to-install-a-build-from-github-on-intellij)

Configuration
-------------

After having `Robot Framework Language Server` installed, some configurations (such as specifying
the python executable used for launching the Language Server or Robot Framework)
may be needed (by default it'll use the `python` from the `PATH`).

The settings may be configured at: `File > Settings > Languages & Frameworks > Robot Framework Language Server`.

Developing
------------

See: [Contributing](docs/contributing.md) for how to help in the development of `Robot Framework Language Server for Intellij`.

Features (1.5.0)
-----------------

- Settings page for the language server (per project and global).
- Code completion.
- Code analysis.
- Outline in Structure view.
- Linting with [Robocop](https://robocop.readthedocs.io/en/latest/).
- Go to definition.
- Hover.
- Code folding.
- Code formatting.
- Browse Keywords (symbols -- note: enable the `robot.workspaceSymbolsOnlyForOpenDocs` when dealing with big workspaces).
- Syntax highlighting (with `semanticTokens/full` request).
- Debugger:
  - Add line breakpoints in `.robot` or `.py` files.
  - Evaluate keywords in debug console/hover/watch.
  - Pause at breakpoints to inspect the stack and see variables.
  - Step in.
  - Step over.
  - Step return.
  - Continue.


See: [Changelog](docs/changelog.md) for details.


License: Apache 2.0
-------------------
