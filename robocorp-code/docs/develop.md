
Developing
-----------

Install NodeJs (https://nodejs.org/en/) -- make sure that `node` and `npm` are in the `PATH`.

Install Yarn (https://yarnpkg.com/) -- make sure that `yarn` is in the `PATH`.

Download the sources, head to the root directory (where `package.json` is located)
and run: `yarn install`.

After this step, it should be possible to open the `robocorp_code` folder in VSCode and launch
`Extension: Robocorp Code` to have a new instance of VSCode with the loaded extension.


Building a VSIX locally
------------------------

To build a VSIX, follow the steps in https://code.visualstudio.com/api/working-with-extensions/publishing-extension
(if everything is setup, `vsce package` from the root directory should do it).


Adding a new command
---------------------

To add a new command, add it at the `COMMANDS` in `/robocorp-code/codegen/commands.py` and then execute
(in a shell in the `/robocorp-code` directory) `python -m dev codegen`.

This should add the command to the `package.json` as well as the files related to the constants.

Then, you may handle the command either in `/robocorp-code/vscode-client/src/extension.ts` if the
command requires some VSCode-only API or in the language server (which is ideal as less work would
be required when porting the extension to a different client).

Note: that it's also possible to have one command call another command, so, if needed the command could start
on the client and then call parts of it on the server.

Note: the code in the extension side (in TypeScript) should be kept to a minimum (as it needs to be
redone if porting to a different client).

Note: at least one integration test for each action must be added in 
`/robocorp-code/tests/robocorp_code_tests/test_vscode_integration.py`


Adding a new setting
---------------------

To add a new setting, add it at the `SETTINGS` in `/robocorp-code/codegen/settings.py` and then execute
(in a shell in the `/robocorp-code` directory) `python -m dev codegen`.

New version release
--------------------

To release a new version:

- Create release branch (`git branch -D release-robocorp-code&git checkout -b release-robocorp-code`)
- Update version (`python -m dev set-version 0.0.4`).
- Update README.md to add notes on features/fixes.
- Update changelog.md to add notes on features/fixes and set release date.
- Push contents to release branch, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.
- Create a tag (`git tag robocorp-code-0.0.4`) and push it.