from convert import convert_case_to_constant


class Command(object):
    def __init__(
        self,
        name,
        title,
        add_to_package_json=True,
        keybinding="",
        server_handled=True,
        icon=None,  # https://microsoft.github.io/vscode-codicons/dist/codicon.html
        enablement=None,
        hide_from_command_palette=False,
        constant="",
    ):
        """
        :param add_to_package_json:
            If a command should not appear to the user, add_to_package_json should be False.
        :param server_handled:
            If True this is a command handled in the server (and not in the client) and
            thus will be registered as such.
        :param constant:
            If given the internal constant used will be this one (used when a command
            is renamed and we want to keep compatibility).
        """
        self.name = name
        self.title = title
        self.add_to_package_json = add_to_package_json
        self.keybinding = keybinding
        self.server_handled = server_handled
        self.icon = icon
        self.enablement = enablement
        self.hide_from_command_palette = hide_from_command_palette
        if not constant:
            constant = convert_case_to_constant(name)
        self.constant = constant


COMMANDS = [
    Command(
        "robocorp.getLanguageServerPython",
        "Get a python executable suitable to start the language server",
        add_to_package_json=False,
        server_handled=False,
    ),
    Command(
        "robocorp.getLanguageServerPythonInfo",
        "Get info suitable to start the language server {pythonExe, environ}",
        add_to_package_json=False,
        server_handled=False,
    ),
    Command(
        "robocorp.getPluginsDir",
        "Get the directory for plugins",
        add_to_package_json=False,
        server_handled=True,
    ),
    # Note: this command is started from the client (due to needing window.showQuickPick)
    # and the proceeds to ask for the server for the actual implementation.
    Command("robocorp.createRobot", "Create Robot", server_handled=False),
    # Internal commands for robocorp.createRobot.
    Command(
        "robocorp.listRobotTemplates.internal",
        "Provides a list with the available robot templates",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.createRobot.internal",
        "Actually calls rcc to create the robot",
        add_to_package_json=False,
        server_handled=True,
    ),
    # Started from the client due to needing UI actions.
    Command(
        "robocorp.uploadRobotToCloud",
        "Upload Robot to the Robocorp Cloud",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.localListRobots.internal",
        "Lists the activities currently available in the workspace",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.isLoginNeeded.internal",
        "Checks if the user is already linked to an account",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.getLinkedAccountInfo.internal",
        "Provides information related to the current linked account",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.cloudLogin",
        "Link to Robocorp Cloud",
        add_to_package_json=True,
        server_handled=False,
        icon="$(link)",
    ),
    Command(
        "robocorp.cloudLogin.internal",
        "Link to Robocorp Cloud (receives credentials)",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.cloudListWorkspaces.internal",
        "Lists the workspaces available for the user (in the Robocorp Cloud)",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.uploadToNewRobot.internal",
        "Uploads a Robot as a new Robot in the Robocorp Cloud",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.uploadToExistingRobot.internal",
        "Uploads a Robot as an existing Robot in the Robocorp Cloud",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.runInRcc.internal",
        "Runs a custom command in RCC",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.runRobotRcc",
        "Run Robot",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.debugRobotRcc",
        "Debug Robot",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.robotsViewTaskRun",
        "Launch selected Task in Robots view",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/run.svg", "dark": "images/dark/run.svg"},
    ),
    Command(
        "robocorp.robotsViewTaskDebug",
        "Debug selected Task in Robots view",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/debug.svg", "dark": "images/dark/debug.svg"},
    ),
    Command(
        "robocorp.saveInDiskLRU",
        "Saves some data in an LRU in the disk",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.loadFromDiskLRU",
        "Loads some LRU data from the disk",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.computeRobotLaunchFromRobocorpCodeLaunch",
        "Computes a robot launch debug configuration based on the robocorp code launch debug configuration",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.setPythonInterpreter",
        "Set pythonPath based on robot.yaml",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.resolveInterpreter",
        "Resolves the interpreter to be used given a path",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.cloudLogout",
        "Unlink and remove credentials from Robocorp Cloud",
        add_to_package_json=True,
        server_handled=False,
        icon="$(circle-slash)",
    ),
    Command(
        "robocorp.cloudLogout.internal",
        "Unlink and remove credentials from Robocorp Cloud internal",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.refreshRobotsView",
        "Refresh Robots view",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/refresh.svg", "dark": "images/dark/refresh.svg"},
    ),
    Command(
        "robocorp.refreshRobotContentView",
        "Refresh Robot Content view",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/refresh.svg", "dark": "images/dark/refresh.svg"},
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.newFileInRobotContentView",
        "New File",
        add_to_package_json=True,
        server_handled=False,
        icon="$(new-file)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.newFolderInRobotContentView",
        "New Folder",
        add_to_package_json=True,
        server_handled=False,
        icon="$(new-folder)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.deleteResourceInRobotContentView",
        "Delete",
        add_to_package_json=True,
        server_handled=False,
        icon="$(close)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.renameResourceInRobotContentView",
        "Rename",
        add_to_package_json=True,
        server_handled=False,
        icon="$(edit)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.refreshCloudView",
        "Refresh Cloud view",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/refresh.svg", "dark": "images/dark/refresh.svg"},
    ),
    Command(
        "robocorp.startBrowserLocator",
        "Start browser to create Locators",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.startBrowserLocator.internal",
        "Start browser to create Locators. Requires the robot where the locators should be saved",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.createLocatorFromBrowserPick",
        "Create Locator from browser pick",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.createLocatorFromScreenRegion",
        "Create Image Locator from screen region",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.createLocatorFromScreenRegion.internal",
        "Create Image Locator from screen region (internal)",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.createLocatorFromBrowserPick.internal",
        "Create Locator from browser pick (internal: provides no UI in case of errors)",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.stopBrowserLocator",
        "Stop browser used to create Locators",
        add_to_package_json=True,
        server_handled=True,
    ),
    Command(
        "robocorp.getLocatorsJsonInfo",
        "Obtain information from the locators.json given a robot.yaml",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.newLocatorUI",
        "Create locator",
        add_to_package_json=True,
        server_handled=False,
        icon="$(plus)",
    ),
    # This is the same as the one above, but it won't ask what's the robot, it'll
    # just use the one selected in the robots tree.
    Command(
        "robocorp.newLocatorUI.tree.internal",
        "New locator",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(plus)",
    ),
    Command(
        "robocorp.copyLocatorToClipboard.internal",
        "Copy locator name to clipboard",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(clippy)",
    ),
    Command(
        "robocorp.openRobotTreeSelection",
        "Open robot.yaml",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(go-to-file)",
    ),
    Command(
        "robocorp.cloudUploadRobotTreeSelection",
        "Upload Robot to Robocorp Cloud",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(cloud-upload)",
    ),
    Command(
        "robocorp.openLocatorTreeSelection",
        "Open locators.json",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(go-to-file)",
        constant="ROBOCORP_OPEN_LOCATOR_TREE_SELECTION",
    ),
    Command(
        "robocorp.rccTerminalCreateRobotTreeSelection",
        "Open terminal with Robot environment",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(terminal)",
        constant="ROBOCORP_CREATE_RCC_TERMINAL_TREE_SELECTION",
    ),
    Command(
        "robocorp.sendMetric",
        "Send metric",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.submitIssue.internal",
        "Submit issue (internal)",
        server_handled=False,
        hide_from_command_palette=True,
    ),
    Command("robocorp.submitIssue", "Submit issue", server_handled=False),
    Command(
        "robocorp.configuration.diagnostics.internal",
        "Robot Configuration Diagnostics (internal)",
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.configuration.diagnostics",
        "Robot Configuration Diagnostics",
        server_handled=False,
    ),
    Command(
        "robocorp.rccTerminalNew",
        "Terminal with Robot environment",
        server_handled=False,
        icon="$(terminal)",
    ),
]


def get_keybindings_for_json():
    keybinds_contributed = []
    for command in COMMANDS:
        if not command.add_to_package_json:
            continue

        if command.keybinding:
            keybinds_contributed.append(
                {
                    "key": command.keybinding,
                    "command": command.name,
                    "when": "editorTextFocus",
                }
            )

    return keybinds_contributed


def get_commands_for_json():
    commands_contributed = []
    for command in COMMANDS:
        if not command.add_to_package_json:
            continue
        dct = {"command": command.name, "title": command.title, "category": "Robocorp"}
        if command.icon:
            dct["icon"] = command.icon
        if command.enablement:
            dct["enablement"] = command.enablement
        commands_contributed.append(dct)

    return commands_contributed


def get_activation_events_for_json():
    activation_events = []
    for command in COMMANDS:
        activation_events.append("onCommand:" + command.name)

    activation_events.append("onDebugInitialConfigurations")
    activation_events.append("onDebugResolve:robocorp-code")

    return activation_events
