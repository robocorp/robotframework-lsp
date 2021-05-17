from convert import convert_case_to_constant
from typing import List


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
        category="Robot Framework",
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
        self.category = category


COMMANDS: List[Command] = [
    Command("robot.runTest", "Run Test/Task", icon="$(play)", server_handled=False),
    Command(
        "robot.debugTest", "Debug Test/Task", icon="$(debug)", server_handled=False
    ),
    Command(
        "robot.runSuite",
        "Run Tests/Tasks Suite",
        icon="$(run-all)",
        server_handled=False,
    ),
    Command(
        "robot.debugSuite",
        "Debug Tests/Tasks Suite",
        icon="$(debug-alt)",
        server_handled=False,
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
        dct = {
            "command": command.name,
            "title": command.title,
            "category": command.category,
        }
        if command.icon:
            dct["icon"] = command.icon
        if command.enablement:
            dct["enablement"] = command.enablement
        commands_contributed.append(dct)

    return commands_contributed


def get_activation_events_for_json():
    activation_events = []

    activation_events.append("onLanguage:robotframework")
    activation_events.append("onDebugInitialConfigurations")
    activation_events.append("onDebugResolve:robotframework-lsp")
    activation_events.append("onCommand:robot.addPluginsDir")
    activation_events.append("onCommand:robot.getLanguageServerVersion")
    activation_events.append("onCommand:robot.getInternalInfo")
    activation_events.append("onCommand:robot.resolveInterpreter")
    activation_events.append("onCommand:robot.listTests")

    for command in COMMANDS:
        activation_events.append("onCommand:" + command.name)

    return activation_events
