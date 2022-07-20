Configuration settings
----------------------

- `robot.language-server.python` this is the python executable used to launch the
  **Language Server** itself. It must point to a python (3.7+) executable. **Note:**
  after changing this setting, the editor needs to be restarted.

- `robot.python.executable` must point to a python executable where **Robot Framework** and user
  libraries are installed (note that it only needs to be set if it's different from `robot.language-server.python`).

- `robot.python.env` can be used to set the environment variables used by the `robot.python.executable`.

- `robot.pythonpath` entries to be added to the PYTHONPATH for **Robot Framework** (used when resolving resources and libraries and automatically passed to the launch config as `--pythonpath` entries).

- `robot.variables` custom variables to be considered by **Robot Framework** (used when resolving variables and automatically passed to the launch config as `--variable` entries).

- `robot.loadVariablesFromArgumentsFile` may point to an arguments file from which variables should be loaded for linting / code-completion.
    - Note: the arguments file still needs to be separately set during launching too.

- `robot.completions.section_headers.form`: can be used to determine if the completions should be presented in the plural or singular form.

- `robot.editor.4spacesTab`: used to put 4 spaces instead of using tabs or indenting to a tab level in the editor (default: true).

- `robot.completions.keywords.format`: used to configure how keywords from libraries will be applied during code-completion.

- `robot.codeFormatter`: used to configure the code-formatter to be used.

- `robot.flowExplorerTheme`: used to configure the Robot Flow Explorer theme to be used.

- `robot.codeLens.enable`: used to configure whether code-lenses should be shown.
      Code lenses available are:
          - Run/Debug (to run or debug a Test/Task)
          - Load in interactive console (to load or run a Session/Keyword/Test/Task in the interactive console).

- `robot.libraries.libdoc.needsArgs`: a list of the libraries for which the arguments need to be passed for the libdoc generation.

- `robot.libraries.libdoc.preGenerate`: a list of the libraries for which the libdoc should be pre-generated
    (note: builtin libraries are always pre-generated and don't need to be added here).



Linting-related settings
--------------------------

- `robot.lint.enabled` can be used to disable the linting altoghether.

- `robot.lint.undefinedKeywords` can be used to disable the linting of undefined keywords altoghether.

- `robot.lint.robocop.enabled`: used to enable/disable linting with [Robocop](https://robocop.readthedocs.io/en/latest/) (default: false).

- `robot.lint.undefinedLibraries`: used to disable the reporting of undefined libraries.

- `robot.lint.undefinedResources`: used to disable the reporting of undefined resources.

- `robot.lint.undefinedVariableImports`: used to disable the reporting of undefined variable imports.

- `robot.lint.keywordCallArguments`: used to disable the reporting of wrong arguments in a keyword call.

- `robot.lint.variables`: used to disable the reporting of undefined variables.

- `robot.lint.ignoreVariables` variables defined with this setting won't be reported as undefined variables during linting.

- `robot.lint.ignoreEnvironmentVariables` environment variables defined with this setting won't be reported as undefined environment variables during linting.

Environment variables
----------------------

Environment variables that affect the debugger:

- `RFLS_KILL_ZOMBIE_PROCESSES`: Set to `true` to kill zombie processes automatically after running
    Robot Framework (default is false since `0.49.0`).

- `RFLS_BREAK_ON_FAILURE`: Set to `true` to stop on failures when debugging in Intellij
    (In VSCode this is handled by the `Robot Log FAIL` in the breakpoints).

- `RFLS_BREAK_ON_ERROR`: Set to `true` to stop on errors when debugging in Intellij
    (In VSCode this is handled by the `Robot Log ERROR` in the breakpoints).

- `RFLS_IGNORE_FAILURES_IN_KEYWORDS`: May be used to set the Keywords in which Robot Failures and Errors
    should not stop the debugger execution nor be reported as errors.

    It's a json-formatted list of keywords where failures should be ignored.

    Note that the list below is always ignored by default (so using `RFLS_IGNORE_FAILURES_IN_KEYWORDS`
    it's possible to add other items to that list).

    ```
    [
        "Run keyword and continue on failure",
        "Run keyword and expect error",
        "Run keyword and ignore error",
        "Run keyword and warn on failure",
        "Wait until keyword succeeds",
        "Try..except"
    ]
    ```

- `RFLS_IGNORE_FAILURES_IN_KEYWORDS_OVERRIDE`: Set to `true` to only load the `RFLS_IGNORE_FAILURES_IN_KEYWORDS` from
    `RFLS_IGNORE_FAILURES_IN_KEYWORDS` and not use any pre-defined entry.

- `ROBOTFRAMEWORK_DAP_LOG_FILENAME`: Path to a filename where logs should be written.


- `ROBOTFRAMEWORK_DAP_LOG_LEVEL`: Log level for the logging (0 to 3).


Development/debug settings
---------------------------

- `robot.language-server.tcp-port`: if specified, connect to the language server previously started at the given port. **Note:**
  after changing this setting, the editor needs to be restarted.

- `robot.language-server.args`: arguments to be passed to the robotframework language server (i.e.: `["-vv", "--log-file=~/robotframework_ls.log"]`). **Note:**
  after changing this setting, the editor needs to be restarted.

Vscode example configs
---------------------------

Below you can find example run configs for your launch.json file inside of the .vscode folder

```
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "type": "robotframework-lsp",
            "name": "Robot with arg file",
            "request": "launch",
            "cwd": "${workspaceFolder}",
            "target": "${file}",
            "terminal": "none",
            "args": [
                "-A${workspaceFolder}/my_arg_file"
            ]
        },
        {
            "type": "robotframework-lsp",
            "name": "Robot with arg file and choice of browser",
            "request": "launch",
            "cwd": "${workspaceFolder}",
            "target": "${file}",
            "terminal": "none",
            "args": [
                "-A${workspaceFolder}/my_arg_file",
                "${input:BrowserType}"
            ]
        },
        {
            "type": "robotframework-lsp",
            "name": "Robot codecheck",
            "request": "launch",
            "cwd": "${workspaceFolder}",
            "target": "${file}",
            "terminal": "none",
            "preLaunchTask": "Robot_code_check"
        },
        {
            "type": "robotframework-lsp",
            "name": "Robot with custom variables",
            "request": "launch",
            "cwd": "${workspaceFolder}",
            "target": "${file}",
            "terminal": "none",
            "env": {
                "PATH": "${env:PATH}:/home/${env:USER}/.robotFrameworkTools",
                "MYVARIABLE": "myvalue"
            }
        }
    ],
    // This is an input which asks the user which browser to use, robot files should use ${BROWSER} variable.
    "inputs": [
        {
            "type": "pickString",
            "id": "BrowserType",
            "description": "Which browser du you want to use?",
            "options": [
                "-v BROWSER:headlesschrome",
                "-v BROWSER:chrome"
            ],
            "default": "-v BROWSER:headlesschrome"
        }
    ]
}
```

Below is an example of a tasks.json file which will go inside the .vscode folder. This task will do a code inspection through a robot --dryrun command

```
{
    // See https://go.microsoft.com/fwlink/?LinkId=733558
    // for the documentation about the tasks.json format
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Robot_code_check",
            "type": "process",
            "isBackground": false,
            "command": "robot",
            "args": [
                "--dryrun",
                "--quiet",
                "${file}"
            ],
            "presentation": {
                "echo": true,
                "reveal": "silent",
                "focus": false,
                "panel": "shared",
                "showReuseMessage": true,
                "clear": false
            }
        }
    ]
}
```
