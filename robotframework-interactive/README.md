[Robot Framework](https://robotframework.org/) Interactive (Interpreter).
=============

Requirements
-------------

Python 3.7+ and [Robot Framework](https://robotframework.org/) 3.2+.


Description
============

A library that provides an API to be able to interactively use Robot Framework.


Developing
============

To develop the library, the recommended way to work with it is changing the launch.json to include an environment variable such as
RF_INTERACTIVE_LOCAL_RESOURCE_ROOT as in the example below, then, running yarn install/yarn watch-build-dev to automatically
regenerate the contents when the webview contents are changed.

"RF_INTERACTIVE_LOCAL_RESOURCE_ROOT": "X:/vscode-robot/robotframework-lsp/robotframework-interactive/vscode-interpreter-webview/dist"
