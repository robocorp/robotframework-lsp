Configuration settings
----------------------

- `robot.language-server.python` this is the python executable used to launch the
  **Language Server** itself. It must point to a python (3.7+) executable. **Note:**
  after changing this setting, the editor needs to be restarted.
  
- `robot.python.executable` must point to a python executable where **Robot Framework** and dependent 
  libraries are installed (note that it only needs to be set if it's different from `robot.language-server.python`).
  
- `robot.python.env` can be used to set the environment used by `robot.python.executable`.

- `robot.variables` custom variables to be considered by **Robot Framework** (used when resolving variables and automatically passed to the launch config as `--variable` entries).

- `robot.pythonpath` entries to be added to the PYTHONPATH for **Robot Framework** (used when resolving resources and imports and automatically passed to the launch config as `--pythonpath` entries).

- `robot.completions.section_headers.form`: can be used to determine if the completions should be presented in the plural or singular form.

- `robot.editor.4spacesTab`: used to put 4 spaces instead of using tabs or indenting to a tab level in the editor (default: true).


Development/debug settings
---------------------------

- `robot.language-server.tcp-port`: if specified, connect to the language server previously started at the given port. **Note:**
  after changing this setting, the editor needs to be restarted.
  
- `robot.language-server.args`: Specifies the arguments to be passed to the robotframework language server (i.e.: `["-vv", "--log-file=~/robotframework_ls.log"]`). **Note:**
  after changing this setting, the editor needs to be restarted.
