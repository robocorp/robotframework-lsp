class Command(object):
    def __init__(
        self, name, title, add_to_package_json=True, keybinding="", server_handled=True
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


COMMANDS = [
    Command(
        "robocorp.getLanguageServerPython",
        "Get a python executable suitable to start the language server.",
        add_to_package_json=False,
        server_handled=False,
    ),
    Command(
        "robocorp.getPluginsDir",
        "Get the directory for plugins.",
        add_to_package_json=False,
        server_handled=True,
    ),
    # Note: this command is started from the client (due to needing window.showQuickPick)
    # and the proceeds to ask for the server for the actual implementation.
    Command(
        "robocorp.createActivity", "Create Activity Package.", server_handled=False
    ),
    # Internal commands for robocorp.createActivity.
    Command(
        "robocorp.listActivityTemplates.internal",
        "Provides a list with the available activity templates.",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.createActivity.internal",
        "Actually calls rcc to create the activity.",
        add_to_package_json=False,
        server_handled=True,
    ),
    # Started from the client due to needing UI actions.
    Command(
        "robocorp.uploadActivityToCloud",
        "Upload Activity Package to the cloud.",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.localListActivities.internal",
        "Lists the activities currently available in the workspace.",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.isLoginNeeded.internal",
        "Checks if the user is already logged in.",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.cloudLogin.internal",
        "Logs into Robocloud.",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.cloudListWorkspaces.internal",
        "Lists the workspaces available for the user (in the cloud).",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.uploadToNewActivity.internal",
        "Uploads an Activity Package as a new Activity Package in the cloud.",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.uploadToExistingActivity.internal",
        "Uploads an Activity Package as an existing Activity Package in the cloud.",
        add_to_package_json=False,
        server_handled=True,
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
        commands_contributed.append(
            {"command": command.name, "title": command.title, "category": "Robocorp"}
        )

    return commands_contributed


def get_activation_events_for_json():
    activation_events = []
    for command in COMMANDS:
        activation_events.append("onCommand:" + command.name)
    return activation_events
