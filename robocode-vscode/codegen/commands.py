class Command(object):
    def __init__(self, name, title, add_to_package_json=True, keybinding=""):
        """
        :param add_to_package_json:
            If a command should not appear to the user, add_to_package_json should be False.
        """
        self.name = name
        self.title = title
        self.add_to_package_json = add_to_package_json
        self.keybinding = keybinding


COMMANDS = [
    Command(
        "robocode.getLanguageServerPython",
        "Get a python executable suitable to start the language server.",
        add_to_package_json=False,
    ),
    Command("robocode.sayHello", "Hello World", add_to_package_json=True),
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
            {"command": command.name, "title": command.title, "category": "Robocode"}
        )

    return commands_contributed


def get_activation_events_for_json():
    activation_events = []
    for command in COMMANDS:
        activation_events.append("onCommand:" + command.name)
    return activation_events
