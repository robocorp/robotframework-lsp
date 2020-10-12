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
- New action to log in Robocloud.
- Terminology update (`Activity Package` is now `Robot`).
- Improvements uploading Robot to cloud.
- Detecting if a robot.yaml is in a workspace root folder and not only in a subfolder.


New in 0.0.4 (2020-09-02)
-----------------------------

- The extension name changed to Robocorp Code (so, if upgrading from 0.0.3, please 
  remove the previous version manually).
- When a package.yaml is found, it's used to provide a different python environment
  when running/debugging `.robot` files using the RobotFramework Language Server.


New in 0.0.3 (2020-08-12)
-----------------------------

- Polishments submiting activity package to the cloud.
- Fixed issue starting RCC after download on Mac.


New in 0.0.2 (2020-08-06)
-----------------------------

- Submit activity package to the cloud (preliminary version)


New in 0.0.1 (2020-07-27)
-----------------------------

- Download rcc (conda manager)
- Use rcc to create conda env to start the language server
- Create an activity using rcc