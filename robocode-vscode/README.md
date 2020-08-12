`Robocode VSCode Extension`

Robocode VSCode Extension is a Visual Studio Code Extension for Software Robot Development by [https://robocorp.com/](https://robocorp.com/).


Requirements
-------------

Windows, Linux or Mac OS.


Installing
-----------

`Robocode VSCode Extension` as a `.vsix`.

To get a `.vsix`, download the latest `Deploy - Robocode VSCode Extension` from [Robotframework-lsp Github Actions](https://github.com/robocorp/robotframework-lsp/actions?query=workflow%3A%22Deploy+-+Robocode+VSCode+Extension%22).

See: [Install from a vsix](https://code.visualstudio.com/docs/editor/extension-gallery#_install-from-a-vsix) for details installing a `.vsix` into VSCode.


Configuration
-------------

After having the extension installed, the first time that the extension is activated
it will download additional dependencies (such as a conda manager) to bootstrap
the actual language server.

Features (0.0.3)
-----------------

- Automatic bootstrap of Python environment for the language server.
  Note that when the `Robocode VSCode Extension` is installed, the `Robot Framework Language Server` will
  also use the same environment by default.
  
- Create a template activity with the `Robocode: Create a Robocode Activity Package.` action.

- Submit an activity package to the cloud with the `Robocode: Upload activity package to the cloud.` action.

Developing
------------

See: [Developing](docs/develop.md) for details on how to develop the `Robocode VScode Extension`.

Reporting Issues
-----------------

See: Issues may be reported at: [https://github.com/robocorp/robotframework-lsp/issues/new/choose](https://github.com/robocorp/robotframework-lsp/issues/new/choose).

License: Apache 2.0
-------------------
