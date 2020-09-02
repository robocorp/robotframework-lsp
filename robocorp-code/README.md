`Robocorp Code Extension`

Robocorp Code Extension is a Visual Studio Code Extension for Software Robot Development by [https://robocorp.com/](https://robocorp.com/).


Requirements
-------------

Windows, Linux or Mac OS.


Installing
-----------

`Robocorp Code Extension` as a `.vsix`.

To get a `.vsix`, download the latest `Deploy - Robocorp Code Extension` from [Robotframework-lsp Github Actions](https://github.com/robocorp/robotframework-lsp/actions?query=workflow%3A%22Deploy+-+Robocorp+Code+Extension%22).

See: [Install from a vsix](https://code.visualstudio.com/docs/editor/extension-gallery#_install-from-a-vsix) for details installing a `.vsix` into VSCode.


Configuration
-------------

After having the extension installed, the first time that the extension is activated
it will download additional dependencies (such as a conda manager) to bootstrap
the actual language server.

Features (0.0.4)
-----------------

Note: If upgrading from 0.0.3, please remove the previous version manually as the name of the extension changed.

- Automatic bootstrap of Python environment for the language server.
  Note that when the `Robocorp Code Extension` is installed, the `Robot Framework Language Server` will
  also use the same environment by default.
  
- Create a template activity with the `Robocorp: Create Activity Package.` action.

- Submit an activity package to the cloud with the `Robocorp: Upload Activity Package to the cloud.` action.

- When a package.yaml is found, it's used to provide a different python environment when running/debugging `.robot` files using the RobotFramework Language Server.
  Note: this only works if no manual customizations were done to the `robot.python.executable` or `robot.pythonpath` settings.

Developing
------------

See: [Developing](docs/develop.md) for details on how to develop the `Robocorp Code Extension`.

Reporting Issues
-----------------

See: Issues may be reported at: [https://github.com/robocorp/robotframework-lsp/issues/new/choose](https://github.com/robocorp/robotframework-lsp/issues/new/choose).

License: Apache 2.0
-------------------
