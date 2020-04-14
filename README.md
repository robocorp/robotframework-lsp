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


Configuration
-------------

After having `robotframework-lsp` installed, some configurations (such as specifying
the python executable used for launching the Language Server or Robot Framework)
may be needed.

See: [Config](docs/config.md) for details.
  

Features (0.0.8)
-----------------

- Launch .robot files (new in 0.0.8)
- Code completion for keywords, section headers and section settings
- Syntax highlighting
- Syntax validation
- Code Formatting

See: [Changelog](docs/changelog.md) for details.


Developing
------------

See: [Developing](docs/develop.md) for details on how to develop `robotframework-lsp` itself.

License: Apache 2.0
-------------------
