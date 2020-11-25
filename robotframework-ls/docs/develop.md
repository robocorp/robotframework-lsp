
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

To build a VSIX, follow the steps in https://code.visualstudio.com/api/working-with-extensions/publishing-extension
(if everything is setup, `vsce package` from the root directory should do it).

New version release
--------------------

To release a new version:

- Open a shell at the proper place (something as `X:\vscode-robot\robotframework-lsp\robotframework-ls`)

- Create release branch (`git branch -D release-robotframework-lsp&git checkout -b release-robotframework-lsp`)

- Update version (`python -m dev set-version 0.6.0`).

- Update README.md to add notes on features/fixes.

- Update changelog.md to add notes on features/fixes and set release date.

- Push contents, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.

- Rebase with master (`git checkout master&git rebase release-robotframework-lsp`).

- Create a tag (`git tag robotframework-lsp-0.6.0`) and push it.

- Send release msg. i.e.:

`Robot Framework Language Server 0.6.0` is now available (both from `pip install robotframework-lsp` or through the `VSCode marketplace`).

The main changes are:

...