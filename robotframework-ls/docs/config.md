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

- `robot.completions.section_headers.form`: can be used to determine if the completions should be presented in the plural or singular form.

- `robot.lint.robocop.enabled`: used to enable/disable linting with [Robocop](https://robocop.readthedocs.io/en/latest/) (default: true).

- `robot.editor.4spacesTab`: used to put 4 spaces instead of using tabs or indenting to a tab level in the editor (default: true).

- `robot.completions.keywords.format`: used to configure how keywords from libraries will be applied during code-completion.


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