Robot Framework Language Server for Intellij
=============================================

Requirements
-------------
Intellij or some other Intellij-based product (such as PyCharm).

Python 3.7+ and [Robot Framework](https://robotframework.org/) 3.2+.

Note: if using the [Robot Framework Selenium Library](https://github.com/robotframework/SeleniumLibrary), version 4.4+ is required.

Important
-----------

The Intellij Language Server integration is currently in alpha for early access.
Please report any issues found during testing.


Installing latest from Github Actions
--------------------------------------

Install the latest from [JetBrains Marketplace](https://plugins.jetbrains.com/plugin/16086-robot-framework-language-server)
from Intellij by accessing `Settings > Plugins` and searching for `Robocorp`.

Installing latest from Github Actions
--------------------------------------

It's also possible to download the latest build from [Tests Intellij](https://github.com/robocorp/robotframework-lsp/actions?query=workflow%3A%22Tests+-+Intellij%22)
from GitHub Actions. Open the latest successful run, download the `intellij-distribution.zip` and unpack it locally, then
head over to Intellij: `File > Settings > Plugins` and choose to `Install Plugin from Disk` (by clicking the `gear` icon in the plugins page),
then, select the `robotframework-intellij-X.X.X.zip` (which was inside of `intellij-distribution.zip`). 

Configuration
-------------

After having `Robot Framework Language Server` installed, some configurations (such as specifying
the python executable used for launching the Language Server or Robot Framework)
may be needed (by default it'll use the `python` from the `PATH`).

The settings may be configured at: `File > Settings > Languages & Frameworks > Robot Framework Language Server`.

Features (0.10.0)
-----------------

- Settings page for the language server (per project and global)
- Code completion
- Code analysis
- Go to definition
- Browse Keywords (symbols -- note: enable the `robot.workspaceSymbolsOnlyForOpenDocs` when dealing with big workspaces)
- Syntax highlighting (with `semanticTokens/full` request).

See: [Changelog](docs/changelog.md) for details.


Developing
------------

See: [Developing](docs/develop.md) for details on how to develop `Robot Framework Language Server`.


License: Apache 2.0
-------------------
