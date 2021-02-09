Robot Framework Language Server for Intellij
=============================================

Requirements
-------------
Intellij or some other Intellij-based product (such as PyCharm).

Python 3.7+ and [Robot Framework](https://robotframework.org/) 3.2+.

Note: if using the [Robot Framework Selenium Library](https://github.com/robotframework/SeleniumLibrary), version 4.4+ is required.

Installing
-----------

Right now it should be possible to install it from the latest [Tests Intellij](https://github.com/robocorp/robotframework-lsp/actions?query=workflow%3A%22Tests+-+Intellij%22) run
from GitHub Actions. Open the latest successful run, download the `intellij-distribution.zip` and unpack it locally, then
head over to Intellij: `File > Settings > Plugins` and choose to `Install Plugin from Disk` (by clicking the `gear` icon in the plugins page),
then, select the `robotframework-intellij-X.X.X.zip` (which was inside of `intellij-distribution.zip`). 

Configuration
-------------

After having `Robot Framework Language Server` installed, some configurations (such as specifying
the python executable used for launching the Language Server or Robot Framework)
may be needed (by default it'll use the `python` from the `PATH`).

The settings may be configured at: `File > Settings > Languages & Frameworks > Robot Framework Language Server`.

Features (0.7.1)
-----------------

- Settings for the language server may be set at `File > Settings > Languages & Frameworks > Robot Framework Language Server`
- Code completion
- Code analysis
- Go to definition
- Browse Keywords (symbols)
- Syntax highlighting (pretty basic right now)

See: [Changelog](docs/changelog.md) for details.


Developing
------------

See: [Developing](docs/develop.md) for details on how to develop `Robot Framework Language Server`.


License: Apache 2.0
-------------------
