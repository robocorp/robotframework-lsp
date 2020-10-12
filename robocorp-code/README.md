`Robocorp Code`

Robocorp Code is a Visual Studio Code extension for Software Robot Development created and maintained by [https://robocorp.com/](https://robocorp.com/).

With the Robocorp Code extension, you can create new software robots, run them locally, and publish them to Robocorp Cloud all from within Visual Studio Code.

Find the full instructions at [https://robocorp.com/docs/setup/robocorp-code](https://robocorp.com/docs/setup/robocorp-code).


Requirements
-------------

[Robot Framework Language Server](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp) extension provides extra Robot Framework related capabilities, including code completion and formatting, as well as syntax validation and highlighting. It is recommended to install it  alongside this Robocorp Code extension.

Supported operating systems:
Windows 10, Linux or Mac OS.


Installation
-----------

Find the full installation instructions at [https://robocorp.com/docs/setup/robocorp-code](https://robocorp.com/docs/setup/robocorp-code).


Configuration
-------------

After installing the extension, the first time the extension is activated
it will download additional dependencies (such as a conda manager) that are required to bootstrap the extension.

Features (0.1.3)
-----------------

- Automatic bootstrapping of Python environment for the `Robot Framework Language Server`.

- Create a Robot from a pre-configured template using the `Robocorp: Create Robot` action.

- Upload a Robot to the cloud with the `Robocorp: Upload Robot to the cloud.` action.

- Log in to the cloud with the `Robocorp: Log in Robocloud.` action.

- When a [robot.yaml](https://robocorp.com/docs/setup/robot-yaml-format) is found, it can utilise a different Python environment when running/debugging `.robot` files using the RobotFramework Language Server.
  Note: this only works if no manual customizations were made to the `robot.python.executable` or `robot.pythonpath` settings.

Developing
------------

See: [Developing](docs/develop.md) for details on how to develop the `Robocorp Code` extension.

Reporting Issues
-----------------

See: Issues may be reported at: [https://github.com/robocorp/robotframework-lsp/issues/new/choose](https://github.com/robocorp/robotframework-lsp/issues/new/choose).

License: Apache 2.0
-------------------
