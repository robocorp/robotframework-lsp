New in 0.28.0 (2022-03-14)
-----------------------------

- Created action: `Robocorp: Clear Robocorp (RCC) environments and restart Robocorp Code`.
- RCC updated to v11.6.6.
- New Windows locator integrated.
- Properly notify of timeouts executing RCC.
- Raised timeout for uploading Robots.
- Fix case where Path and PATH could conflict on Windows.
- Pre-releases now available from VSCode marketplace.


New in 0.27.1 (2022-02-04)
-----------------------------

- Fix issue where run failed with error if vault connection was not set.

New in 0.27.0 (2022-02-03)
-----------------------------

- It's now possible to use the online vault secrets from within VSCode.
  - A new `Vault` item is added to the `Robocorp` view which allows setting the workspace for the vault.
  - Note: each new run obtains a new token (valid for 2 hours) to communicate with the vault.


New in 0.26.0 (2022-01-26)
-----------------------------

- The organization is shown when listing workspaces for workspace upload.
- Robot tasks are expanded by default.
- Fixed case where the computed pythonpath entries for a Robot could be wrong.


New in 0.25.0 (2022-01-19)
-----------------------------

- The Python extension interpreter is automatically set to use the Robot environment
  - It's possible to opt out by setting `robocorp.autoSetPythonExtensionInterpreter` to `false`.
  - Action now uses `python.defaultInterpreterPath` or the new (unreleased) API to set the interpreter if available.
- The Robot Framework Language Server `0.37.0` is now required for a critical fix:
  - Handle the case where the target robot is passed as an array for resolving the interpreter (launching with the test explorer could fail due to this).


New in 0.24.0 (2022-01-17)
-----------------------------

- RCC updated to v11.6.3
- The extension now runs with `-v` by default (to show info level messages on `OUTPUT > Robocorp Code`).


New in 0.23.0 (2021-12-22)
-----------------------------

- RCC downgraded to v11.5.5 to avoid regression in v11.6.0
- Environment variables from env.json are properly escaped (new line chars are now properly handled).
- Minimum Robot Framework Language Server version required is now 0.35.0
- Minimum VSCode version required is now 1.61.0


New in 0.22.0 (2021-12-15)
-----------------------------

- Selecting html file in Robot content view properly opens it in external browser by default.


New in 0.21.0 (2021-12-14)
-----------------------------

- RCC updated to v11.6.0.

- robocorp-inspector updated to 0.5.0.

- When sending an issue a confirmation is shown.

- Robots view:
  - A Robot is always auto-selected if available in the workspace.
  - A proper message is shown to guide users on the case where there's no Robot in the workspace.
  - Added option to reveal in explorer.
  - Added button to create new robot.
  - Context menu filled with actions.

- Robot content view:
  - Added option to reveal in explorer.
  - Context menu filled with actions to open file externally or internally.
  - When clicking an item, it's opened even if already selected.

- Robocorp view:
  - Updated labels

- Improvements in the upload Robot UI.
  - Labels
  - Workspaces that the user cannot read are no longer shown.


New in 0.20.0 (2021-11-16)
-----------------------------

- It's now possible to create a Robot in the workspace root folder. [#497](https://github.com/robocorp/robotframework-lsp/issues/497)
- Clicking on inspector button multiple times no longer opens multiple inspectors. [#493](https://github.com/robocorp/robotframework-lsp/issues/493)
- When creating an environment, its output is shown in the `Output` tab interactively and the last line is shown in the progress. [#491](https://github.com/robocorp/robotframework-lsp/issues/491)
- RCC updated to `11.5.5`.


New in 0.19.0 (2021-11-08)
-----------------------------

- When a command line is too big to be launched in the terminal, a wrapper script is used [#394](https://github.com/robocorp/robotframework-lsp/issues/394)
- The default is now launching in the terminal and not in the debug console.


New in 0.18.0 (2021-11-01)
-----------------------------

- When relocating robot, make sure that the `PYTHONPATH` entries are properly forwarded.
- Robot Framework Language Server `0.26.0` is now required.


New in 0.17.0 (2021-10-21)
-----------------------------

- In the Robot view, the commands related to `Robot` and `Task` items are now shown inline.
- The extension now handles the case where an `env.json` with non-string values is used.
- RCC updated to 11.4.2
- When a `work item` selection is cancelled, the related launch is also cancelled.
- When `ROBOCORP_OVERRIDE_SYSTEM_REQUIREMENTS` is set, it's now possible to initialize the extension.


New in 0.16.0 (2021-10-13)
-----------------------------

- Notify of errors during initialization of extension.
- Fix `ROBOT_ROOT` when environment is reused.
- Update RCC to v11.3.2 .
- Improved Robot Template selection from RCC.
- Work items support:
  - See: [Using Work Items](https://robocorp.com/docs/developer-tools/visual-studio-code/extension-features#using-work-items) for details.
  - Variables should not be defined in `env.json` anymore and the support is simplified to only accept items in `devdata/work-items-in` and `devdata/work-items-out`.
  - `devdata/work-items-in` is expected to be added to source conrtol (i.e.: `git`), whereas `devdata/work-items-out` is expected to be ignored.
  - The `RPA_OUTPUT_WORKITEM_PATH` is now set automatically to a new folder in `work-items-out`
    - Later it's possible to convert this folder into an input by using the button which appears in the item in the work items view.
  - When a run is made, it should present a dialog which allows the input selection (to set to `RPA_INPUT_WORKITEM_PATH`)
    - Note that it's possible to use some output in `devdata/work-items-out` as the input for the next run.
  - Only the last 5 runs are kept in the output. To keep older items, rename the folder or move it to `devdata/work-items-in`.
  - For previously existing items, those should be moved to `devdata/work-items-in` so that they are shown.
  - Changing `env.json` should not be needed anymore (in fact, changes to the related variables will be ignored to avoid clashes with other tools).
  - The latest `rpaframework` is required for the integration.


New in 0.15.0 (2021-10-04)
-----------------------------

- Update to RCC v11.2.0.
- If the Robot Framework Language Server is not installed, python debug launches can still resolve the interpreter.


New in 0.14.0 (2021-09-21)
-----------------------------

- Robocorp panel redesigned.
- robocorp-inspector updated to 0.3.8.

New in 0.13.3 (2021-09-08)
-----------------------------

- Fix case where the python used in debug did not match the one used in the environment.
- Two different `conda.yaml` files with only cosmetic changes (such as comments) now map to the same environment.
- Fixes related to `TEMP` directories managed in the environment.
- The default `cwd` when resolving environments is now properly managed so that conflicts don't arise due to having a `robot.yaml` in the `cwd`.
- `--controller` is properly set when making an `rcc` run.


New in 0.13.2 (2021-09-06)
-----------------------------

- Improved detection of whether an environment is corrupt to regenerate it when starting the extension.
- Fixes in inspector integration.


New in 0.13.1 (2021-08-31)
-----------------------------

- Critical fix: if the base environment was removed the extension could fail to initialize.


New in 0.13.0 (2021-08-30)
-----------------------------

- Improved UI is now used to create and edit browser and image locators.
- If it was not possible to create some environment, it won't be retried until the `conda.yaml` is changed or `VSCode` is restarted.
- The language server environment is no longer refreshed on startup (so startup is faster).

New in 0.12.1 (2021-08-23)
-----------------------------

- At most 10 environment are created, using Holotree from RCC (environments are now recycled).
- Upgraded to RCC 10.7.0.
- Deal with `pythonDeprecatePythonPath` when setting the python executable path for vscode-python from a Robot.
- If the Robot Framework Language Server extension is installed in VSCode, at least 0.21.0 is now required.


New in 0.11.1 (2021-05-27)
-----------------------------

- Fixed issue where the Robot environment wasn't being properly forwarded when debugging a plain python Robot.


New in 0.11.0 (2021-05-26)
-----------------------------

- The Robocorp view now has a tree showing the contents of the currently selected robot.
- RCC upgraded to 9.16.0.


New in 0.10.0 (2021-05-12)
-----------------------------

- Support to create a terminal with access to the environment of a `Robot`.
  - It's accessible in the Robot tree view or by executing the `Robocorp: Terminal with Robot environment` action.


New in 0.9.2 (2021-04-21)
-----------------------------

- Fix issue where completions were requested on .yaml files when that shouldn't be the case.
- Support for robot tasks with a `shell` or `robotTaskName`.


New in 0.9.1 (2021-04-19)
-----------------------------

- Upgrade to RCC 9.9.15.


New in 0.9.0 (2021-04-08)
-----------------------------

- New action: `Robocorp: Robot Configuration Diagnostics` to validate a Robot on request.
- Robot configuration is now validated automatically when a `robot.yaml` or `conda.yaml` is opened or saved.


New in 0.8.2 (2021-03-29)
-----------------------------

- Ignoring environment variables starting with `=` (which could end up breaking the language server startup).


New in 0.8.1 (2021-03-24)
-----------------------------

- Upgrade to RCC 9.7.4.


New in 0.8.0 (2021-02-24)
-----------------------------

- Upgrade to RCC 9.4.3. #242
- Fix creating browser locator with rpaframework-core 6.0.0.
- New `Robocorp: Submit issue` command.
  - Allows reporting issues to Robocorp from within VSCode.
  - Attaches logging and system information.


New in 0.7.1 (2021-01-22)
-----------------------------

- Fixed issue starting Robocorp Code on Mac OS and Linux.

New in 0.7.0 (2021-01-20)
-----------------------------

- Tree for Robocorp Cloud info. #225
  - Link credentials.
  - Unlink credentials.
  - Refresh.
  - Workspaces/Robots available.
- Cloud credentials not entered in Robocorp Code are no longer used as a fallback. #230
- Credentials now stored as `robocorp-code` instead of `--robocorp-code`.
- Upload Robot selected in Robots tree to the cloud.
- Check that the Windows Long Path support is enabled. #235
- Metrics for feature usage. #234
- Properly uploading to a new Robot in the cloud. #229


New in 0.6.2 (2021-01-07)
-----------------------------

- Update RCC to version 7.1.5. #227


New in 0.6.1 (2020-12-28)
-----------------------------

- Improved support for `Image Locators` #220
    - Command to create a new `Image Locator` available from the Locators tree.
    - Command to open selected locator from the Locators tree.
    - When hovering over a `"path"` or `"source"` element in the `locators.json`, a preview is shown.
- If the Robot Framework Language Server extension is not installed, suggest its installation. #212

New in 0.6.0 (2020-12-21)
-----------------------------

- Improved support for [locators](https://robocorp.com/docs/development-howtos/browser/how-to-find-user-interface-elements-using-locators-in-web-applications):
    - Locators from locators.json are shown in the Locators tree.
    - An action to create a new `Browser Locator' by selecting an element in a browser is now available in the tree.
    - When hovering over a `"screenshot"` element in the `locators.json`, a preview is shown.

New in 0.5.3 (2020-12-08)
-----------------------------

- Update RCC to version 7.0.4. #206

New in 0.5.2 (2020-12-02)
-----------------------------

- Unlink user from Robocorp Cloud

New in 0.5.1 (2020-11-29)
-----------------------------

- If `ROBOCORP_HOME` has spaces in the path, detect it and ask for a new path without spaces. #200
- Created `robocorp.home` setting to specify `ROBOCORP_HOME`.

New in 0.5.0 (2020-11-25)
-----------------------------

- New Robots view (lists robots and allows launching/debugging them). #183
- New action to set the pythonPath to be used by the Python extension based on the `robot.yaml`. #185
- Templates available now have a description. #181
- The account used to login is now tied to Robocorp Code. #189
- Initial debug configurations are now provided. #184
- Upgraded to use RCC v6.1.3. #194

New in 0.4.0 (2020-11-08)
-----------------------------

- Plain python Robot Tasks from `robot.yaml` can now also be debugged (note:
  the Python plugin must also be installed). #179
- In the login action, pressing enter without any information will open the
  proper url to obtain the credentials. #177
- If there's only one task to run in the workspace, use it in the Debug/Run Robot
  action. #175
- Upgraded to use RCC v4.


New in 0.3.0 (2020-10-26)
-----------------------------

- Debugging Robot Tasks from `robot.yaml` is now available
  (as long as they start with `python -m robot` and finish with the folder/filename to be run).


New in 0.2.0 (2020-10-15)
-----------------------------

- Launching Robot Tasks from `robot.yaml` is now available.


New in 0.1.3 (2020-10-12)
-----------------------------

- Improved logo
- Feedback metrics incorporated.


New in 0.1.2 (2020-10-01)
-----------------------------

- If a workspace cannot be loaded, other (valid) workspaces should still be loaded. #164


New in 0.1.1 (2020-09-29)
-----------------------------

- Make sure that we use rcc env variables from robot.yaml in the launch too. #159


New in 0.1.0 (2020-09-29)
-----------------------------

- Properly load devdata/env.json when available.


New in 0.1.0 (2020-09-28)
-----------------------------

- Updated logo
- First version to be published to the VSCode marketplace.


New in 0.0.5 (2020-09-23)
-----------------------------

- Working with [robot.yaml](https://robocorp.com/docs/setup/robot-yaml-format) instead of the deprecated `package.yaml`.
- New action to log in Robocorp Cloud.
- Terminology update (`Activity Package` is now `Robot`).
- Improvements uploading Robot to Robocorp Cloud.
- Detecting if a robot.yaml is in a workspace root folder and not only in a subfolder.


New in 0.0.4 (2020-09-02)
-----------------------------

- The extension name changed to Robocorp Code (so, if upgrading from 0.0.3, please
  remove the previous version manually).
- When a package.yaml is found, it's used to provide a different python environment
  when running/debugging `.robot` files using the RobotFramework Language Server.


New in 0.0.3 (2020-08-12)
-----------------------------

- Polishments submiting activity package to the Robocorp Cloud.
- Fixed issue starting RCC after download on Mac.


New in 0.0.2 (2020-08-06)
-----------------------------

- Submit activity package to the Robocorp Cloud (preliminary version)


New in 0.0.1 (2020-07-27)
-----------------------------

- Download rcc (conda manager)
- Use rcc to create conda env to start the language server
- Create an activity using rcc
