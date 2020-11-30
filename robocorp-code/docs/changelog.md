New in X.X.X (XXXX-XX-XX)
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