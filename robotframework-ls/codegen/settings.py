SETTINGS = {
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
    "robot.loadVariablesFromArgumentsFile": {
        "type": "string",
        "default": "",
        "description": "Load variables for code-completion and code-analysis based on an arguments file. Multiple files accepted by separating with a comma.",
    },
    "robot.pythonpath": {
        "type": "array",
        "default": [],
        "description": 'Entries to be added to the PYTHONPATH (used when resolving resources and imports and automatically passed to the launch config as --pythonpath entries).\n(i.e.: ["c:/my/pro/src"])',
    },
    "robot.libraries.libdoc.needsArgs": {
        "type": "array",
        "default": ["remote", "fakerlib"],
        "description": 'Libraries which will generate a different set of keywords based on the arguments provided.\n(i.e.: ["remote", "fakerlib"])',
    },
    "robot.libraries.libdoc.preGenerate": {
        "type": "array",
        "default": [],
        "description": "List of libraries which should have the libspec pre-generated.",
    },
    "robot.codeFormatter": {
        "type": "string",
        "default": "builtinTidy",
        "description": "Allows the configuration of the code-formatter engine to be used.\nOne of: robotidy, builtinTidy.",
        "enum": ["robotidy", "builtinTidy"],
    },
    "robot.flowExplorerTheme": {
        "type": "string",
        "default": "dark",
        "description": "Allows the configuration of the Robot Flow Explorer theme to be used.\nOne of: dark, light.",
        "enum": ["dark", "light"],
    },
    "robot.lint.robocop.enabled": {
        "type": "boolean",
        "default": False,
        "description": "Specifies whether to lint with Robocop.",
    },
    "robot.lint.enabled": {
        "type": "boolean",
        "default": True,
        "description": "Determines whether linting should be enabled.",
    },
    "robot.lint.undefinedKeywords": {
        "type": "boolean",
        "default": True,
        "description": "Reports undefined keywords when linting.",
    },
    "robot.lint.undefinedLibraries": {
        "type": "boolean",
        "default": True,
        "description": "Reports undefined libraries when linting.",
    },
    "robot.lint.undefinedResources": {
        "type": "boolean",
        "default": True,
        "description": "Reports undefined resources when linting.",
    },
    "robot.lint.undefinedVariableImports": {
        "type": "boolean",
        "default": True,
        "description": "Reports undefined variable imports when linting.",
    },
    "robot.lint.keywordCallArguments": {
        "type": "boolean",
        "default": True,
        "description": "Reports issues in keyword call arguments.",
    },
    "robot.lint.keywordResolvesToMultipleKeywords": {
        "type": "boolean",
        "default": True,
        "description": "Reports whenever a keyword call would resolve to more than one keyword.",
    },
    "robot.lint.variables": {
        "type": "boolean",
        "default": True,
        "description": "Reports issues in undefined variables.",
    },
    "robot.lint.ignoreVariables": {
        "type": "array",
        "default": [],
        "description": 'Don\'t report undefined variables for these variables (i.e.: ["Var1", "Var2"]).',
    },
    "robot.lint.ignoreEnvironmentVariables": {
        "type": "array",
        "default": [],
        "description": 'Don\'t report undefined environment variables for these variables (i.e.: ["VAR1", "VAR2"]).',
    },
    "robot.lint.unusedKeyword": {
        "type": "boolean",
        "default": False,
        "description": "Reports whether a keyword is not used anywhere in the workspace.",
    },
    "robot.completions.section_headers.form": {
        "type": "string",
        "default": "plural",
        "description": "Defines how completions should be shown for section headers (i.e.: *** Setting(s) ***).\nOne of: plural, singular, both.",
        "enum": ["plural", "singular", "both"],
    },
    "robot.completions.keywordsNotImported.enable": {
        "type": "boolean",
        "default": True,
        "description": "Defines whether to show completions for keywords not currently imported (adds the proper import statement when applied).",
    },
    "robot.completions.keywordsNotImported.addImport": {
        "type": "boolean",
        "default": True,
        "description": "Defines whether to actually add the import statement when applying completions showing keywords not currently imported.",
    },
    "robot.completions.keywords.format": {
        "type": "string",
        "default": "",
        "description": "Defines how keyword completions should be applied.\nOne of: First upper, Title Case, ALL UPPER, all lower.",
        "enum": ["First upper", "Title Case", "ALL UPPER", "all lower"],
    },
    "robot.completions.keywords.prefixImportName": {
        "type": "boolean",
        "default": False,
        "description": "Defines whether completions showing keywords should prefix completions with the module name.",
    },
    "robot.completions.keywords.prefixImportNameIgnore": {
        "type": "array",
        "default": [],
        "description": 'Defines module names for which the name should not be prefixed when applying a completion (i.e.: ["builtin"]).',
    },
    "robot.completions.keywords.argumentsSeparator": {
        "type": "string",
        "default": "    ",
        "description": "Defines the string used to separate arguments when applying a Keyword completion with arguments.",
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
    "robot.quickFix.keywordTemplate": {
        "type": "string",
        "default": "$keyword_name$keyword_arguments\n    $cursor\n\n",
        "description": "The template to be used for keyword creation in quick fixes.",
    },
    "robot.codeLens.enable": {
        "type": "boolean",
        "default": True,
        "description": "Enables or disables all Robot Framework code-lenses.",
    },
    "robot.codeLens.run.enable": {
        "type": "boolean",
        "default": True,
        "description": "Enables or disables the Run/Debug code-lenses.",
    },
    "robot.codeLens.interactiveConsole.enable": {
        "type": "boolean",
        "default": True,
        "description": "Enables or disables the Interactive Console code-lenses.",
    },
    "robot.interactiveConsole.arguments": {
        "type": "array",
        "default": [],
        "description": 'The arguments with the options to be used to start an interactive console. i.e.: ["--output", "${workspaceRoot}/interactive_output.xml"]',
    },
    "robot.language": {
        "type": "array",
        "default": [],
        "description": "Language(s) to be used in Robot Framework (passed as the --language argument for robot when launching).",
    },
    "robot.run.peekError.level": {
        "type": "string",
        "enum": ["NONE", "INFO", "WARN", "ERROR"],
        "default": "ERROR",
        "description": "Defines the log level for the messages shown on the peek error window.",
    },
    "robot.run.peekError.showSummary": {
        "type": "boolean",
        "default": False,
        "description": "Defines whether a message should be shown at the task/test level with a summary of the errors.",
    },
    "robot.run.peekError.showErrorsInCallers": {
        "type": "boolean",
        "default": True,
        "description": "Defines whether a message should be shown at each keyword caller when a keyword fails.",
    },
}


def get_settings_for_json():
    return SETTINGS
