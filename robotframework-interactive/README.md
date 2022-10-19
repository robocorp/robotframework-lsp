# [Robot Framework](https://robotframework.org/) Interactive (Interpreter).

## Requirements

Python 3.7+ and [Robot Framework](https://robotframework.org/) 3.2+.

# Description

A library that provides an API to be able to interactively use Robot Framework.

# Developing

To develop the library run `yarn install`/`yarn watch-build-dev` to automatically
regenerate the contents when the webview contents are changed.

Note: make sure that the vendored version of the library is not present in
`robotframework-ls/src/robotframework_ls/vendored` (as the default is getting
the vendored version and if not available search for the dev version).
