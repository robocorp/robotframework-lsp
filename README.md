[Language Server Protocol](https://github.com/Microsoft/language-server-protocol) for [Robot Framework](https://robotframework.org/)
=======

Requirements
-------------

Python 3.7+ and [Robot Framework](https://robotframework.org/) 3.2+ (note that [Robot Framework](https://robotframework.org/)) may
be installed in a separate python interpreter in case you need to run it with an older version of Python).


Installing
-----------

`robotframework-lsp` can be installed from the [VisualStudio Marketplace](https://marketplace.visualstudio.com/items?itemName=robocorptech.robotframework-lsp) or as a `.vsix`.

To get a `.vsix`, download the latest `Deploy Extension` in [Robotframework-lsp Github Actions](https://github.com/robocorp/robotframework-lsp/actions).

See: [Install from a vsix](https://code.visualstudio.com/docs/editor/extension-gallery#_install-from-a-vsix) for details installing a `.vsix` into VSCode.


Configuration
-------------

After having `robotframework-lsp` installed, some settings may need to be configured:

- the `robot.language-server.python` may need to be configured to point to a Python 3.7+ interpreter so that the
  Language Server can be started (after changing this setting, VSCode itself may need to be restarted).
  
- the `robot.python.executable` must point to a Python installation where `robotframework` and dependent 
  libraries are installed.
  
- the `robot.python.env` can be used to set the environment used by `robot.python.executable`.

- the `robot.variables` can be used to set custom variables which would usually be passed in the command line to `robotframework`.
  

Features (0.0.4)
-----------------

- Syntax highlighting
- Syntax validation
- Code-completion for section headers
- Code-completion for section settings


Developing
-----------

Install NodeJs (https://nodejs.org/en/) -- make sure that `node` and `npm` are in the `PATH`.

Install Yarn (https://yarnpkg.com/) -- make sure that `yarn` is in the `PATH`.

Download the sources, head to the root directory (where `package.json` is located)
and run: `yarn install`.

After this step, it should be possible to open the `roboframework-lsp` folder in VSCode and launch
`Extension: Roboframework-lsp` to have a new instance of VSCode with the loaded extension.


Building a VSIX locally
------------------------

To build a VSIX, follow the steps in https://code.visualstudio.com/api/working-with-extensions/publishing-extension.

New version release
--------------------

To release a new version:

- Update version (python -m dev set-version 0.0.4)
- Update this README to add notes on features/fixes
- Create a tag in the format below and push it:
  git tag robotframework-lsp-0.0.0

License: Apache 2.0
-------------------
