import os.path

from commands import (
    get_activation_events_for_json,
    get_commands_for_json,
    get_keybindings_for_json,
    COMMANDS,
)
from convert import convert_case_to_constant
from settings import get_settings_for_json, SETTINGS
import views


def get_menus():
    ret = views.get_menus()
    commands_palette_entry = []
    for command in COMMANDS:
        if command.hide_from_command_palette:
            commands_palette_entry.append({"command": command.name, "when": "false"})
    if commands_palette_entry:
        ret["commandPalette"] = commands_palette_entry
    return ret


def get_json_contents():
    from robocorp_code import __version__

    base_package_contents = {
        "name": "robocorp-code",
        "displayName": "Robocorp Code",
        "description": "Extension for Robot development in VSCode using Robocorp Cloud",
        "author": "Fabio Zadrozny",
        "homepage": "https://github.com/robocorp/robotframework-lsp/blob/master/robocorp-code/README.md",
        "repository": {
            "type": "git",
            "url": "https://github.com/robocorp/robotframework-lsp.git",
        },
        "license": "SEE LICENSE IN LICENSE.txt",
        "version": __version__,
        "icon": "images/icon.png",
        "publisher": "robocorp",
        "engines": {"vscode": "^1.53.0"},
        "categories": ["Debuggers"],
        "activationEvents": get_activation_events_for_json()
        + views.get_activation_events_for_json()
        + ["onLanguage:json", "onLanguage:yaml"],
        "contributes": {
            "configuration": {
                "title": "Robocorp Code Language Server Configuration",
                "type": "object",
                "properties": get_settings_for_json(),
            },
            "viewsContainers": views.get_views_containers(),
            "views": views.get_tree_views(),
            "languages": [],
            "grammars": [],
            "debuggers": [
                {
                    "type": "robocorp-code",
                    "label": "Robocorp Code",
                    "languages": [],
                    "configurationAttributes": {
                        "launch": {
                            "properties": {
                                "robot": {
                                    "type": "string",
                                    "description": "The robot.yaml file with the task to be launched.",
                                    "default": "${file}",
                                },
                                "task": {
                                    "type": "string",
                                    "description": "The task name from the robot to be run.",
                                },
                                "args": {
                                    "type": "array",
                                    "description": "Additional command line arguments for running the robot.",
                                },
                                "env": {
                                    "type": "object",
                                    "description": "Environment variables to be added to the launch.",
                                },
                                # We may want to add it in the future, but for now this is unsupported,
                                # as we only support using the debug console.
                                # "terminal": {
                                #     "type": "string",
                                #     "enum": ["none", "integrated", "external"],
                                #     "enumDescriptions": [
                                #         "No terminal (pipes the output to the client debug console).",
                                #         "Use terminal integrated in client.",
                                #         "External terminal (configured in user settings).",
                                #     ],
                                #     "description": "The terminal to launch the program.",
                                #     "default": "none",
                                # },
                            }
                        }
                    },
                    "configurationSnippets": [
                        {
                            "label": "Robocorp Code: Launch task from robot.yaml",
                            "description": "Add a new configuration for launching tasks from a robot.yaml.",
                            "body": {
                                "type": "robocorp-code",
                                "name": "Robocorp Code: Launch task from robot.yaml",
                                "request": "launch",
                                # "terminal": "none",
                                "robot": '^"\\${file}"',
                                "task": "",
                            },
                        }
                    ],
                }
            ],
            "keybindings": get_keybindings_for_json(),
            "commands": get_commands_for_json(),
            "menus": get_menus(),
        },
        "main": "./vscode-client/out/extension",
        "scripts": {
            "vscode:prepublish": "cd vscode-client && npm run compile && cd ..",
            "compile": "cd vscode-client && tsc -p ./ && cd ..",
            "watch": "cd vscode-client && tsc -watch -p ./ && cd ..",
            "pretest": "cd vscode-client && tsc -p ./ && cd ..",
            "test": "node ./vscode-client/out/tests/runTests.js",
        },
        "devDependencies": {
            "@types/mocha": "^2.2.32",
            "@types/node": "^11.0.40",
            "@types/vscode": "1.53.0",
            "vscode-test": "1.5.1",
            "typescript": "^3.8.2",
        },
        "dependencies": {
            "vscode-languageclient": "^7.0.0-next.12",
            "path-exists": "^4.0.0",
            "http-proxy-agent": "^2.1.0",
            "https-proxy-agent": "^2.2.4",
            "vscode-nls": "^4.1.2",
        },
    }
    return base_package_contents


def write_to_package_json():
    import json

    json_contents = get_json_contents()
    as_str = json.dumps(json_contents, indent=4)
    root = os.path.dirname(os.path.dirname(__file__))
    package_json_location = os.path.join(root, "package.json")
    with open(package_json_location, "w") as stream:
        stream.write(as_str)
    print("Written: %s" % (package_json_location,))


root_dir = os.path.dirname(os.path.dirname(__file__))
vscode_js_client_src_dir = os.path.join(root_dir, "vscode-client", "src")
vscode_py_src_dir = os.path.join(root_dir, "src")


def write_js_views():
    from views import TREE_VIEW_CONTAINERS

    views_ts_file = os.path.join(vscode_js_client_src_dir, "robocorpViews.ts")

    command_constants = []

    for tree_view_container in TREE_VIEW_CONTAINERS:
        tree_view_container_id = convert_case_to_constant(
            "tree_view_container_" + tree_view_container.id
        )
        command_constants.append(
            'export const %s = "%s";  // %s'
            % (
                tree_view_container_id,
                tree_view_container.id,
                tree_view_container.title,
            )
        )
        for tree_view in tree_view_container.tree_views:
            tree_view_id = convert_case_to_constant("tree_view_" + tree_view.id)
            command_constants.append(
                'export const %s = "%s";  // %s'
                % (tree_view_id, tree_view.id, tree_view_container.title)
            )

    with open(views_ts_file, "w") as stream:
        stream.write(
            "// Warning: Don't edit file (autogenerated from python -m dev codegen).\n\n"
            + "\n".join(command_constants)
        )
    print("Written: %s" % (views_ts_file,))


def write_js_commands():
    commands_ts_file = os.path.join(vscode_js_client_src_dir, "robocorpCommands.ts")

    command_constants = []

    for contributed_command in COMMANDS:
        command_id = contributed_command.name
        command_name = contributed_command.constant
        command_constants.append(
            'export const %s = "%s";  // %s'
            % (command_name, command_id, contributed_command.title)
        )

    with open(commands_ts_file, "w") as stream:
        stream.write(
            "// Warning: Don't edit file (autogenerated from python -m dev codegen).\n\n"
            + "\n".join(command_constants)
        )
    print("Written: %s" % (commands_ts_file,))


def write_py_commands():
    commands_py_file = os.path.join(vscode_py_src_dir, "robocorp_code", "commands.py")

    command_constants = []

    all_server_commands = []

    for contributed_command in COMMANDS:
        command_id = contributed_command.name
        command_name = contributed_command.constant
        command_constants.append(
            '%s = "%s"  # %s' % (command_name, command_id, contributed_command.title)
        )
        if contributed_command.server_handled:
            all_server_commands.append(command_name)

    with open(commands_py_file, "w") as stream:
        stream.write(
            "# Warning: Don't edit file (autogenerated from python -m dev codegen).\n\n"
            + "\n".join(command_constants)
        )

        stream.write("\n\nALL_SERVER_COMMANDS = [\n    ")
        stream.write(",\n    ".join(all_server_commands))
        stream.write(",\n]\n")
    print("Written: %s" % (commands_py_file,))


def write_py_settings():
    settings_py_file = os.path.join(vscode_py_src_dir, "robocorp_code", "settings.py")

    settings_template = [
        """# Warning: Don't edit file (autogenerated from python -m dev codegen).
"""
    ]

    setting_constant_template = '%s = "%s"'

    # Create the constants
    for setting in SETTINGS:
        # : :type setting: Setting
        settings_template.append(
            setting_constant_template
            % (convert_case_to_constant(setting.name), setting.name)
        )

    settings_template.append(
        """
ALL_ROBOCORP_OPTIONS = frozenset(
    ("""
    )

    for setting in SETTINGS:
        # : :type setting: Setting
        settings_template.append(f"        {convert_case_to_constant(setting.name)},")

    settings_template.append(
        """    )
)
"""
    )

    with open(settings_py_file, "w") as stream:
        stream.write("\n".join(settings_template))

    print("Written: %s" % (settings_py_file,))


def write_js_settings():
    settings_ts_file = os.path.join(vscode_js_client_src_dir, "robocorpSettings.ts")
    settings_template = [
        """// Warning: Don't edit file (autogenerated from python -m dev codegen).

import { ConfigurationTarget, workspace } from "vscode";

export function get<T>(key: string): T | undefined {
    var dot = key.lastIndexOf('.');
    var section = key.substring(0, dot);
    var name = key.substring(dot + 1);
    return workspace.getConfiguration(section).get(name);
}
"""
    ]

    setting_constant_template = 'export const %s = "%s";'

    # Create the constants
    for setting in SETTINGS:
        # : :type setting: Setting
        settings_template.append(
            setting_constant_template
            % (convert_case_to_constant(setting.name), setting.name)
        )

    getter_template = """
export function get%s(): %s {
    let key = %s;
    return get<%s>(key);
}
"""

    setter_template = """
export async function set%s(value): Promise<void> {
    let key = %s;
    let i = key.lastIndexOf('.');
    
    let config = workspace.getConfiguration(key.slice(0, i));
    await config.update(key.slice(i + 1), value, ConfigurationTarget.Global);
}
"""

    # Create the getters / setters
    for setting in SETTINGS:
        js_type = setting.js_type or setting.setting_type
        if js_type == "array":
            raise AssertionError("Expected js_type for array.")
        name = "_".join(setting.name.split(".")[1:])
        name = name.title().replace(" ", "").replace("_", "").replace("-", "")
        settings_template.append(
            getter_template
            % (name, js_type, convert_case_to_constant(setting.name), js_type)
        )

        settings_template.append(
            setter_template % (name, convert_case_to_constant(setting.name))
        )

    with open(settings_ts_file, "w") as stream:
        stream.write("\n".join(settings_template))

    print("Written: %s" % (settings_ts_file,))


def main():
    write_to_package_json()

    write_js_views()
    write_js_commands()
    write_js_settings()

    write_py_commands()
    write_py_settings()


if __name__ == "__main__":
    main()
