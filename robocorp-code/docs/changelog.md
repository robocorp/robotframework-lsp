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