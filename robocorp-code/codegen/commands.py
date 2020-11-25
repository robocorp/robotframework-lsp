class Command(object):
    def __init__(
        self,
        name,
        title,
        add_to_package_json=True,
        keybinding="",
        server_handled=True,
        icon=None,
        enablement=None,
    ):
        """
        :param add_to_package_json:
            If a command should not appear to the user, add_to_package_json should be False.
        :param server_handled:
            If True this is a command handled in the server (and not in the client) and
            thus will be registered as such.
        """
        self.name = name
        self.title = title
        self.add_to_package_json = add_to_package_json
        self.keybinding = keybinding
        self.server_handled = server_handled
        self.icon = icon
        self.enablement = enablement


COMMANDS = [
    Command(
        "robocorp.getLanguageServerPython",
        "Get a python executable suitable to start the language server",
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
        "Checks if the user is already logged in",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.cloudLogin",
        "Log in Robocorp Cloud",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.cloudLogin.internal",
        "Log in Robocorp Cloud (receives credentials)",
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
        "robocorp.refreshRobotsView",
        "Refresh Robots view",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/refresh.svg", "dark": "images/dark/refresh.svg"},
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
