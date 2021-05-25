import os.path


def get_json_contents():
    from robotframework_ls import __version__
    from commands import get_commands_for_json
    from commands import get_activation_events_for_json

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
            "menus": {
                "editor/title/run": [
                    {
                        "command": "robot.runSuite",
                        "title": "Run Tests/Tasks Suite",
                        "group": "1_run@robot_run1",
                        "when": "resourceExtname == .robot && !isInDiffEditor",
                    },
                    {
                        "command": "robot.debugSuite",
                        "title": "Debug Tests/Tasks Suite",
                        "group": "1_run@robot_run2",
                        "when": "resourceExtname == .robot && !isInDiffEditor",
                    },
                ],
                "explorer/context": [
                    {
                        "command": "robot.runSuite",
                        "title": "Run Tests/Tasks Suite",
                        "group": "9_robot_run@1",
                        "when": "resourceExtname == .robot || explorerResourceIsFolder",
                    },
                    {
                        "command": "robot.debugSuite",
                        "title": "Debug Tests/Tasks Suite",
                        "group": "9_robot_run@2",
                        "when": "resourceExtname == .robot || explorerResourceIsFolder",
                    },
                ],
            },
            "semanticTokenScopes": [
                {
                    "scopes": {
                        "header": ["entity.name.type.class.robot"],
                        "setting": ["storage.type.setting.robot"],
                        "name": ["entity.other.inherited-class.robot"],
                        "variableOperator": ["keyword.operator.variable.robot"],
                        "settingOperator": ["keyword.operator.setting.robot"],
                        "keywordNameDefinition": ["entity.name.function.robot"],
                        "keywordNameCall": ["meta.keyword.call.robot"],
                        "control": ["keyword.control.flow.robot"],
                        "testCaseName": ["entity.name.function.robot"],
                        "parameterName": ["variable.parameter.robot"],
                        "argumentValue": ["string.quoted.single.robot"],
                    }
                }
            ],
            "configuration": {
                "title": "Robot Framework Language Server Configuration",
                "type": "object",
                "properties": {
                    "robot.language-server.python": {
                        "type": "string",
                        "default": "",
                        "description": "Path to the python executable used to start the Robot Framework Language Server (the default is searching python on the PATH).\nRequires a restart to take effect.",
                    },
                    "robot.language-server.args": {
                        "type": "array",
                        "default": [],
                        "description": 'Arguments to be passed to the Robot Framework Language Server (i.e.: ["-vv", "--log-file=~/robotframework_ls.log"]).\nRequires a restart to take effect.',
                    },
                    "robot.language-server.tcp-port": {
                        "type": "number",
                        "default": 0,
                        "description": "If the port is specified, connect to the language server previously started at the given port.\nRequires a restart to take effect.",
                    },
                    "robot.python.executable": {
                        "type": "string",
                        "default": "",
                        "description": "Secondary python executable used to load user code and dependent libraries (the default is using the same python used for the language server).",
                    },
                    "robot.python.env": {
                        "type": "object",
                        "default": {},
                        "description": 'Environment variables used to load user code and dependent libraries.\n(i.e.: {"MY_ENV_VAR": "some_value"})',
                    },
                    "robot.variables": {
                        "type": "object",
                        "default": {},
                        "description": 'Custom variables passed to RobotFramework (used when resolving variables and automatically passed to the launch config as --variable entries).\n(i.e.: {"EXECDIR": "c:/my/proj/src"})',
                    },
                    "robot.pythonpath": {
                        "type": "array",
                        "default": [],
                        "description": 'Entries to be added to the PYTHONPATH (used when resolving resources and imports and automatically passed to the launch config as --pythonpath entries).\n(i.e.: ["c:/my/pro/src"])',
                    },
                    "robot.lint.robocop.enabled": {
                        "type": "boolean",
                        "default": False,
                        "description": "Specifies whether to lint with Robocop.",
                    },
                    "robot.completions.section_headers.form": {
                        "type": "string",
                        "default": "plural",
                        "description": "Defines how completions should be shown for section headers (i.e.: *** Setting(s) ***).\nOne of: plural, singular, both.",
                        "enum": ["plural", "singular", "both"],
                    },
                    "robot.completions.keywords.format": {
                        "type": "string",
                        "default": "",
                        "description": "Defines how keyword completions should be applied.\nOne of: First upper, Title Case, ALL UPPER, all lower.",
                        "enum": ["First upper", "Title Case", "ALL UPPER", "all lower"],
                    },
                    "robot.workspaceSymbolsOnlyForOpenDocs": {
                        "type": "boolean",
                        "default": False,
                        "description": "Collecting workspace symbols can be resource intensive on big projects and may slow down code-completion, in this case, it's possible collect info only for open files on big projects.",
                    },
                    "robot.editor.4spacesTab": {
                        "type": "boolean",
                        "default": True,
                        "description": "Replaces the key stroke of tab with 4 spaces. Set to 'false' to active VSCode default.",
                    },
                },
            },
            "languages": [
                {
                    "id": "robotframework",
                    "aliases": ["Robot Framework", "robotframework"],
                    "extensions": [".robot", ".resource"],
                    "configuration": "./language-configuration.json",
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
                    "when": "editorTextFocus && editorLangId == robotframework && !editorHasSelection && !inSnippetMode && !suggestWidgetVisible && config.robot.editor.4spacesTab",
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
                                    "type": "string",
                                    "description": "The .robot file or a folder containing .robot files to be launched.",
                                    "default": "${file}",
                                },
                                "args": {
                                    "type": "array",
                                    "description": "The command line arguments passed to the target.",
                                },
                                "cwd": {
                                    "type": "string",
                                    "description": "The working directory for the launch.",
                                    "default": "${workspaceFolder}",
                                },
                                "env": {
                                    "type": "object",
                                    "description": "Environment variables to be added to the launch.",
                                },
                                "makeSuite": {
                                    "type": "boolean",
                                    "description": "When running, always create a suite for the current folder and then filter the target (to automatically load __init__.robot).",
                                    "default": True,
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
                                    "default": "none",
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
                                "terminal": "none",
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
        "scripts": {
            "vscode:prepublish": "cd vscode-client && npm run compile && cd ..",
            "compile": "cd vscode-client && tsc -p ./ && cd ..",
            "watch": "cd vscode-client && tsc -watch -p ./ && cd ..",
        },
        "dependencies": {
            "path-exists": "^4.0.0",
            "vscode-languageclient": "^7.0.0-next.12",
            "jsonc-parser": "^2.0.3",
        },
        "devDependencies": {
            "@types/mocha": "^2.2.32",
            "@types/node": "^11.0.40",
            "@types/vscode": "1.53.0",
            "vscode-test": "1.5.1",
            "typescript": "^3.8.2",
        },
        "engines": {"vscode": "^1.53.0"},
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
            "# Warning: Don't edit file (autogenerated from python -m dev codegen).\nfrom typing import List\n\n"
            + "\n".join(command_constants)
        )

        stream.write("\n\nALL_SERVER_COMMANDS: List[str] = [\n    ")
        if all_server_commands:
            stream.write(",\n    ".join(all_server_commands))
            stream.write(",\n]\n")
        else:
            stream.write("\n]\n")
    print("Written: %s" % (commands_py_file,))


root_dir = os.path.dirname(os.path.dirname(__file__))
vscode_js_client_src_dir = os.path.join(root_dir, "vscode-client", "src")
vscode_py_src_dir = os.path.join(root_dir, "src")


def main():
    write_to_package_json()

    write_py_commands()


if __name__ == "__main__":
    main()
