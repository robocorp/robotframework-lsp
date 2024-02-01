
Developing
-----------

Install NodeJs (https://nodejs.org/en/) -- make sure that `node` and `npm` are in the `PATH`.

Install Yarn (https://yarnpkg.com/) -- make sure that `yarn` is in the `PATH`.

Download the sources, head to the root directory (where `package.json` is located)
and run: `yarn install`.

After this step, it should be possible to open the `robocorp_code` folder in VSCode and launch
`Extension: Robocorp Code` to have a new instance of VSCode with the loaded extension.


Creating a local environment for python development
----------------------------------------------------

For local development, `poetry` should be used to install the libraries needed,
so, head on to `/robocorp-code` and do `poetry install` to get your python
environment setup.

If everything went well, just pointing your IDE to use the python executable
at .venv/Scripts/python should suffice.

-- in VSCode that'd be using the `Python: Select Interpreter` command.


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


Updating the dependencies needed
---------------------------------

The dependencies are set based in `/robocorp/bin/create_env/condaXXX.yaml` files.
When one of the conda-yaml files are updated, one needs to:

Log into the Robocorp Control Room (sorry, you have to be an employee for that
right now), then go to `Environment pre-builts`, then go to `Unattended Processes`, 
and run the related processes with `Run with input data`, passing the related 
`conda.yaml` files as input data.

After the runs are done, the file:

`/robocorp-code/vscode-client/src/rcc.ts`

needs to be updated to set the `BASENAME_PREBUILT_XXX` global variables based
on the new paths.

Also, the `pyproject.toml` should be updated so that the python development environment
is updated accordingly.


Updating RCC
--------------------

- Open a shell at the proper place (something as `X:\vscode-robot\robotframework-lsp\robocorp-code`)

- Update version (`python -m dev set-rcc-version v11.14.5`).

- Remove the rcc executable from the `bin` folder to redownload the next time the extension is executed.

