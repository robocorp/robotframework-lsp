import os.path


def get_submenus():
    return [{"id": "robotsubmenu", "label": "Robot Framework"}]


def get_menus():
    from commands import COMMANDS

    ret = {
        "editor/title/run": [
            {
                "command": "robot.runSuite",
                "group": "1_run@robot_run1",
                "when": "resourceExtname == .robot && !isInDiffEditor",
            },
            {
                "command": "robot.debugSuite",
                "group": "1_run@robot_run2",
                "when": "resourceExtname == .robot && !isInDiffEditor",
            },
        ],
        "explorer/context": [
            {"submenu": "robotsubmenu", "group": "9_robot.group"},
        ],
        "robotsubmenu": [
            {
                "command": "robot.runSuite",
                "group": "1_run@1",
                "submenu": "robotsubmenu",
                "when": "resourceExtname == .robot || explorerResourceIsFolder",
            },
            {
                "command": "robot.debugSuite",
                "group": "1_run@2",
                "submenu": "robotsubmenu",
                "when": "resourceExtname == .robot || explorerResourceIsFolder",
            },
            {
                "command": "robot.lint.explorer",
                "group": "2_analysis",
                "submenu": "robotsubmenu",
                "when": "resourceExtname == .robot || resourceExtname == .resource || explorerResourceIsFolder",
            },
        ],
        "view/title": [
            {
                "command": "robot.view.documentation.pin",
                "when": "view == robot.view.documentation && !robot.view.documentation.isPinned",
                "group": "navigation",
            },
            {
                "command": "robot.view.documentation.unpin",
                "when": "view == robot.view.documentation && robot.view.documentation.isPinned",
                "group": "navigation",
            },
        ],
    }
    commands_palette_entry = []
    for command in COMMANDS:
        if command.hide_from_command_palette:
            commands_palette_entry.append({"command": command.name, "when": "false"})
    if commands_palette_entry:
        ret["commandPalette"] = commands_palette_entry
    return ret


def collect_views_containers():
    ret = {
        "panel": [
            {
                "id": "robot-documentation",
                "title": "Robot Documentation",
                "icon": "$(notebook)",
            },
            {
                "id": "robot-output",
                "title": "Robot Output",
                "icon": "$(output)",
            },
        ],
    }

    return ret


def collect_views():
    ret = {
        "robot-documentation": [
            {
                "type": "webview",
                "id": "robot.view.documentation",
                "name": "Robot Documentation",
                "contextualTitle": "Robot Documentation",
            }
        ],
        "robot-output": [
            {
                "type": "webview",
                "id": "robot.view.output",
                "name": "Robot Output",
                "contextualTitle": "Robot Output",
            }
        ],
    }

    return ret


def get_json_contents():
    from robotframework_ls import __version__
    from commands import get_commands_for_json
    from commands import get_activation_events_for_json
    from settings import get_settings_for_json

    base_package_contents = {
        "name": "robotframework-lsp",
        "displayName": "Robot Framework Language Server",
        "description": "VSCode extension support for Robot Framework",
        "author": "Fabio Zadrozny",
        "homepage": f"https://github.com/robocorp/robotframework-lsp/blob/robotframework-lsp-{__version__}/robotframework-ls/README.md",
        "repository": {
            "type": "git",
            "url": "https://github.com/robocorp/robotframework-lsp.git",
        },
        "bugs": {"url": "https://github.com/robocorp/robotframework-lsp/issues"},
        "license": "Apache 2.0",
        "version": f"{__version__}",
        "icon": "images/icon.png",
        "publisher": "robocorp",
        "categories": ["Linters", "Programming Languages", "Debuggers"],
        "keywords": ["Robot", "Robot Framework", "multi-root ready"],
        "activationEvents": get_activation_events_for_json(),
        "galleryBanner": {"theme": "dark", "color": "#000000"},
        "contributes": {
            "commands": get_commands_for_json(),
            "submenus": get_submenus(),
            "menus": get_menus(),
            "semanticTokenScopes": [
                {
                    "scopes": {
                        "header": ["entity.name.type.class.robot"],
                        "setting": ["storage.type.setting.robot"],
                        "name": ["entity.other.inherited-class.robot"],
                        "variableOperator": ["keyword.operator.variable.robot"],
                        "settingOperator": ["keyword.operator.setting.robot"],
                        "keywordNameDefinition": ["entity.name.function.robot"],
                        "keywordNameCall": [
                            "meta.keyword.call.robot",
                            "meta.support.function.robot",
                            "entity.name.label.robot",
                            "support.function.robot",
                        ],
                        "control": ["keyword.control.flow.robot"],
                        "testCaseName": ["entity.name.function.robot"],
                        "parameterName": ["variable.parameter.robot"],
                        "argumentValue": ["string.quoted.single.robot"],
                        "error": ["token.error-token.robot", "invalid.illegal.robot"],
                        "documentation": [
                            "comment.block.documentation.robot",
                            "comment.line.documentation.robot",
                            "meta.documentation.robot",
                        ],
                    }
                }
            ],
            "configuration": {
                "title": "Robot Framework Language Server Configuration",
                "type": "object",
                "properties": get_settings_for_json(),
            },
            "viewsContainers": collect_views_containers(),
            "views": collect_views(),
            "languages": [
                {
                    "id": "robotframework",
                    "aliases": ["Robot Framework", "robotframework"],
                    "extensions": [".robot", ".resource"],
                    "configuration": "./language-configuration.json",
                    "icon": {
                        "light": "./images/light.svg",
                        "dark": "./images/dark.svg",
                    },
                }
            ],
            "grammars": [
                {
                    "language": "robotframework",
                    "scopeName": "source.robot",
                    "path": "./syntaxes/robotframework.tmLanguage.json",
                }
            ],
            "keybindings": [
                {
                    "key": "tab",
                    "command": "type",
                    "args": {"text": "    "},
                    "when": "editorTextFocus && editorLangId == robotframework && !editorHasSelection && !inSnippetMode && !suggestWidgetVisible && config.robot.editor.4spacesTab && !inlineSuggestionVisible",
                }
            ],
            "breakpoints": [{"language": "robotframework"}],
            "debuggers": [
                {
                    "type": "robotframework-lsp",
                    "label": "Robot Framework",
                    "languages": ["robotframework"],
                    "configurationAttributes": {
                        "launch": {
                            "properties": {
                                "target": {
                                    "type": ["string", "array"],
                                    "description": "The .robot file or a folder containing .robot files to be launched. Note: a suite will be created from suiteTarget or cwd and further filtering is done with the target.",
                                    "default": "${file}",
                                },
                                "args": {
                                    "type": "array",
                                    "description": "The command line arguments passed to the target.",
                                },
                                "cwd": {
                                    "type": "string",
                                    "description": "The working directory for the launch (also used to create suite if suiteTarget is not specified and makeSuite is true).",
                                    "default": "${workspaceFolder}",
                                },
                                "env": {
                                    "type": "object",
                                    "description": "Environment variables to be added to the launch.",
                                },
                                "makeSuite": {
                                    "type": "boolean",
                                    "description": "If specified, creates a suite from suiteTarget or cwd and applies filtering based on the target (to automatically load __init__.robot).",
                                    "default": True,
                                },
                                "suiteTarget": {
                                    "type": ["string", "array"],
                                    "description": "If specified, a suite will be created from the given target (by default, if not specified, it will be created from cwd).",
                                    "default": "",
                                },
                                "terminal": {
                                    "type": "string",
                                    "enum": ["none", "integrated", "external"],
                                    "enumDescriptions": [
                                        "No terminal (pipes the output to the client debug console).",
                                        "Use terminal integrated in client.",
                                        "External terminal (configured in user settings).",
                                    ],
                                    "description": "The terminal to launch the program.",
                                    "default": "integrated",
                                },
                            }
                        }
                    },
                    "configurationSnippets": [
                        {
                            "label": "Robot Framework: Launch .robot file",
                            "description": "Add a new configuration for launching Robot Framework.",
                            "body": {
                                "type": "robotframework-lsp",
                                "name": "Robot Framework: Launch .robot file",
                                "request": "launch",
                                "cwd": '^"\\${workspaceFolder}"',
                                "target": '^"\\${file}"',
                                "terminal": "integrated",
                                "env": {},
                                "args": [],
                            },
                        },
                        {
                            "label": "Robot Framework: Launch template",
                            "description": "This configuration may be used to customize launches which start from a code-lens or command shortcut.",
                            "body": {
                                "type": "robotframework-lsp",
                                "name": "Robot Framework: Launch template",
                                "request": "launch",
                            },
                        },
                    ],
                }
            ],
        },
        "main": "./vscode-client/out/extension",
        "prettier": {"tabWidth": 4, "printWidth": 120, "quoteProps": "preserve"},
        "scripts": {
            "vscode:prepublish": "cd vscode-client && npm run compile && cd ..",
            "compile": "cd vscode-client && tsc -p ./ && cd ..",
            "watch": "cd vscode-client && tsc -watch -p ./ && cd ..",
            "prettier": "npx prettier -c vscode-client/**/*.ts",
            "prettier-fix": "npx prettier -w vscode-client/**/*.ts",
        },
        "dependencies": {
            "path-exists": "^4.0.0",
            "vscode-languageclient": "^8.0.1",
            "jsonc-parser": "^2.0.3",
            "marked": "^4.1.0",
        },
        "devDependencies": {
            "@types/mocha": "^2.2.32",
            "@types/node": "^13.0.00",
            "@types/vscode": "1.65.0",
            "prettier": "2.4.1",
            "vscode-test": "1.5.1",
            "typescript": "^4.5.4",
        },
        "engines": {"vscode": f"^1.65.0"},
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


def write_py_commands():
    from commands import COMMANDS

    commands_py_file = os.path.join(
        vscode_py_src_dir, "robotframework_ls", "commands.py"
    )

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
            "# fmt: off\n"
            "# Warning: Don't edit file (autogenerated from python -m dev codegen).\nfrom typing import List\n\n"
            + "\n".join(command_constants)
        )

        stream.write("\n\nALL_SERVER_COMMANDS: List[str] = [\n    ")
        if all_server_commands:
            stream.write(",\n    ".join(all_server_commands))
            stream.write(",\n]\n")
        else:
            stream.write("\n]\n")
        stream.write("\n# fmt: on\n")
    print("Written: %s" % (commands_py_file,))


def write_py_settings():
    from convert import convert_case_to_constant
    import settings

    settings_template = [
        """# Warning: Don't edit file (autogenerated from python -m dev codegen).
"""
    ]

    setting_constant_template = '%s = "%s"'

    # Create the constants
    for setting_name in settings.SETTINGS.keys():
        settings_template.append(
            setting_constant_template
            % ("OPTION_" + convert_case_to_constant(setting_name), setting_name)
        )

    settings_template.append(
        """
ALL_ROBOT_OPTIONS = frozenset(
    ("""
    )

    for setting_name in settings.SETTINGS.keys():
        settings_template.append(
            f"        OPTION_{convert_case_to_constant(setting_name)},"
        )

    settings_template.append(
        """    )
)
"""
    )

    for settings_py_file in (
        os.path.join(
            vscode_py_src_dir,
            "robotframework_ls",
            "impl",
            "robot_generated_lsp_constants.py",
        ),
        os.path.join(
            vscode_py_src_dir,
            "..",
            "..",
            "robotframework-interactive",
            "src",
            "robotframework_interactive",
            "server",
            "rf_interpreter_generated_lsp_constants.py",
        ),
    ):

        with open(settings_py_file, "w") as stream:
            stream.write("# fmt: off\n")
            stream.write("\n".join(settings_template))
            stream.write("\n# fmt: on\n")

        print("Written: %s" % (settings_py_file,))


root_dir = os.path.dirname(os.path.dirname(__file__))
vscode_js_client_src_dir = os.path.join(root_dir, "vscode-client", "src")
vscode_py_src_dir = os.path.join(root_dir, "src")


def run_intellij_codegen():
    """
    The Intellij codegen is dependent on the package.json too, so, let's run it
    too.
    """
    import sys
    from pathlib import Path

    target = Path(root_dir) / ".." / "robotframework-intellij"
    assert target.exists(), f"{target} does not exist"
    sys.path.append(str(target))
    import codegen_intellij  # noqa

    codegen_intellij.main()


def main():
    write_to_package_json()

    write_py_commands()

    write_py_settings()

    run_intellij_codegen()


if __name__ == "__main__":
    main()
