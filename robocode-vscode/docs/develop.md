
Developing
-----------

Install NodeJs (https://nodejs.org/en/) -- make sure that `node` and `npm` are in the `PATH`.

Install Yarn (https://yarnpkg.com/) -- make sure that `yarn` is in the `PATH`.

Download the sources, head to the root directory (where `package.json` is located)
and run: `yarn install`.

After this step, it should be possible to open the `robocode_vscode` folder in VSCode and launch
`Extension: Robocode VSCode` to have a new instance of VSCode with the loaded extension.


Building a VSIX locally
------------------------

To build a VSIX, follow the steps in https://code.visualstudio.com/api/working-with-extensions/publishing-extension
(if everything is setup, `vsce package` from the root directory should do it).

New version release
--------------------

To release a new version:

- Update version (`python -m dev set-version 0.0.X`).
- Update README.md to add notes on features/fixes.
- Update changelog.md to add notes on features/fixes and set release date.
- Push contents to release branch, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.
- Create a tag (`git tag robocode-vscode-0.0.X`) and push it.