## Robocorp VS Code extension

The Robocorp extension makes it easy to create Python based automation projects.

You can use this extension as part of the [Robocorp Automation Stack](https://github.com/robocorp/rcc), which has been optimized for tasks such as robotic process automation (RPA), web scraping and IT automation. It scales up from simple image fetching or API calling all the way to complex process automation workflows.

Main features include:

-   **Automatic configuration of dependencies** - Every Python oriented project uses its own lightweight virtual environment and runs in isolation.

-   **Inspector for Web, Windows Application Elements & more** - Pick elements from different mediums and create locators for automation

-   **Create, run and debug projects** - Do these with ease while developing Tasks to automate applications

-   **Deploy projects to Robocorp Cloud** - Run unattended automation in a safe, reliable and easy to use Cloud Platform.

> Note: the use of cloud-based orchestration in [Robocorp Cloud](https://robocorp.com/robocorp-cloud) requires a free account.

![Example of a Robot running with the extension](images/gif_run.gif)

### Get Started

1. Download [Robocorp VS Code extension - basic tutorial](https://robocorp.com/portal/robot/robocorp/example-vscode-basics), and open it in VS Code.

2. Open the command palette - (Windows, Linux): `CTRL-SHIFT-P` (macOS): `CMD-SHIFT-P`

3. Select the command `Robocorp: Run Robot`

![image of command palette](images/command-palette.png)

4. Select the Task to run (only if the Task Package contains more than one task).

> Note: You can do the same actions from the side bar after opening the Extension tab in VS Code.

Find more examples and tutorials at the [Robocorp Portal](https://robocorp.com/robots/).
You can also find helpful videos on the [YouTube Robocorp channel](https://youtu.be/zQQl8xZkGko?list=PLfXJKwwF049DIZxvwYuBgahHcDDGPpfN6).

Full instructions are available at the [Product Manual](https://robocorp.com/docs/product-manuals/robocorp-code) for the VS Code Extension.

This is under active development, so please [contact us](#Reporting-Issues) for issues and feature requests.

### Requirements

Supported operating systems: Windows 10, Linux or Mac OS.

The [Robot Framework Language Server](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp) extension provides extra Robot Framework related capabilities, including code completion and formatting, as well as syntax validation and highlighting. It is highly recommended to install it alongside this Robocorp Code extension.

### Installation

Find the full installation instructions at [https://robocorp.com/docs/product-manuals/robocorp-code](https://robocorp.com/docs/product-manuals/robocorp-code).

### Configuration

During the first activation, the extension will download additional dependencies (such as Conda manager) that are required for it to run.

### Features (1.16.0)

-   Preliminary support for [Robo](https://github.com/robocorp/robo) (Robocorp's Python Framework for automation).
    -   Ctrl+Click on terminal for the 'Robocorp html Log` opens external browser.
    -   Code Lenses to `Run Task` / `Debug Task` for tasks decorated with `@task`.
    -   `ROBO TASKS OUTPUT` which shows the output of tasks run with `@task`.
-   Support for [Work Items](https://robocorp.com/docs/developer-tools/visual-studio-code/extension-features#using-work-items).
-   Automatic bootstrapping of the Python environment for the `Robot Framework Language Server`.
-   Create a Robot from a pre-configured template using the `Robocorp: Create Robot` action.
-   Upload a Robot to the cloud with the `Robocorp: Upload Robot to the Robocorp Cloud` action.
-   Link to the cloud with the `Robocorp: Link to Robocorp Cloud` action.
-   Unlink from the cloud with the `Robocorp: Unlink and remove credentials from Robocorp Cloud` action.
-   Verify Robot for inconsistencies with `Robocorp: Robot Configuration Diagnostics` action.
-   Create a terminal with a Robot environment through the `Robocorp: Terminal with Robot environment` action.
-   Run a Robot with the `Robocorp: Run Robot` action.
-   Debug a Robot with the `Robocorp: Debug Robot` action. - It's possible to debug plain Python tasks using the Python extension or Robot Framework tasks using the Robot Framework Language Server (in which case the task must start with `python -m robot` and finish with the folder/filename to be run).
-   When a [robot.yaml](https://robocorp.com/docs/setup/robot-yaml-format) is found, it utilises the related Python environment when running/debugging `.robot` files using the RobotFramework Language Server.
-   Set the pythonPath configuration to get code completion in the Python extension through the `Set pythonPath based on robot.yaml` action.
-   View, launch and debug Robots from the `Robots` view.
-   View and create new [Browser Locators](https://robocorp.com/docs/development-howtos/browser/how-to-find-user-interface-elements-using-locators-in-web-applications) from the `Locators` view.
-   View and create new [Image Locators](https://robocorp.com/docs/product-manuals/robocorp-lab/locating-and-targeting-user-interface-elements-in-robocorp-lab) from the `Locators` view.
-   When hovering over a `"screenshot"`, `"path"` or `"source"` element in the `locators.json`, a preview is shown.
-   Send issue reports with the `Robocorp: Submit issue` action.
-   Robocorp Inspector is now integrated within the extension - access it from the side bar or via command palette

### Developing

See: [Developing](docs/develop.md) for details on how to develop the `Robocorp Code` extension.

### Reporting Issues

Issues may be reported in the [GitHub Issues](https://github.com/robocorp/robotframework-lsp/issues/new/choose).

Contact us via Slack: [robocorp-developers.slack.com](https://robocorp-developers.slack.com/ssb/redirect)

## License: Apache 2.0
