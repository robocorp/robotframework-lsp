Robot Framework Language Server FAQ
======================================

How to proceed if Keywords from a library are not being resolved?
------------------------------------------------------------------

The most common reason this happens is because some error happened when trying to automatically generate the libspec for
a given library.

If you're in `VSCode`, the error may be seen in the `OUTPUT` tab, selecting `Robot Framework` in the dropdown.

For `Intellij`, it's possible to see it by turning on the logging
(see [Reporting Issues](reporting_issues.md) for details -- look for `EXCEPTION` in the log files).

**Important**: After the logs are collected, revert the changes to stop the logging
(having the logging on may make the language server go slower).

The common errors here are:

**1. The library requires arguments to be initialized**

In this case there are 2 different approaches that can be used:

**a.** Change the library to have default arguments so that libspec can generate it out of the box.

    After the library is changed to accept default arguments, you may need to restart your editor/IDE to clear the related caches.

**b.** Manually generate the libspec for the library and put it somewhere in your workspace or right below a folder in
the `PYTHONPATH`.

    It is possible to manually generate a libspec by executing something as:
    
    `python -m robot.libdoc <library_name> <library_name.libspec>`
    
    Notes:
    
      - `-a` may be used to specify an argument
      - In RobotFramework 3.x `--format XML:HTML` must also be passed
      - See `python -m robot.libdoc -h` for more details
    
    Whenever the library changes, make sure you manually regenerate the libspec.

**2. The library is not present in the python executable you're using.**

In this case, install the library in the given python executable or choose a different python executable which has the
library installed.

    After the library is installed, you may need to restart your editor/IDE to clear the related caches.
    
**3. The library requires runtime information to be imported.**

In this case, please change the library so that it doesn't need runtime information to be imported.
i.e.: generating the `.libspec` as `python -m robot.libdoc <library_name> <library_name.libspec>` requires the
library to be imported. If it cannot be imported it's not possible to generate its libspec (and thus the
language server cannot collect its information).

    After the library is changed, you may need to restart your editor/IDE to clear the related caches.

How to specify a variable needed to resolve some library or resource import?
-----------------------------------------------------------------------------

In this case, the full path needed to resolve the variable needs to be specified in a variable in the `robot.variables`
setting (relative paths or paths requiring other variables aren't currently supported).

i.e.: Given a resource import such as: `Resource ${some_variable}/my.resource`,
`robot.variables` must be set to `{"some_variable": "c:/my/project/src"}`.



How to enable/disable autoformat on save on VSCode?
---------------------------------------------------

1. Open command palette (`Ctrl+Shift+P`) and select the command `Preferences: Configure Language Specific Settings ...`.

2. Select `Robot Framework (robotframework)`

3. After the `settings.json` is opened, type in:

```
  "[robotframework]": {
      "editor.formatOnSave": true
  },
```

How to configure the Robocop linter?
---------------------------------------

To configure the linter create a `.robocop` file in your workspace root and fill it with the values you want.

Note: a `.robocop` file is a file with command line options to configure `Robocop`,

See: https://robocop.readthedocs.io/en/latest/user_guide.html for details on the available command line options.

Example of `.robocop` file:

```
--exclude missing-doc-testcase
--exclude missing-doc-suite
```

How to enable the Robocop linter?
---------------------------------------

To enable the `Robocop` linter, change the setting:

`robot.lint.robocop.enabled`

to `true` (in the Intellij UI, it's the `Lint Robocop Enabled` setting).


How to change the Robocop version used?
-------------------------------------------

The language server will initially try to load the version available from the
`robot.python.executable` that's being used (which defaults to the same version used to start up the language server
itself), so, if you want to use a different
`Robocop` version, just install it so that it's importable in the proper Python environment (note: the minimun `Robocop`
version is `1.6.1`).

Note that a default version is also shipped (but it may not be the latest `Robocop`
version).


How to install a build from GitHub on Intellij?
------------------------------------------------

First download the `distribution-intellij.zip` from one of the [Tests Intellij](https://github.com/robocorp/robotframework-lsp/actions?query=workflow%3A%22Tests+-+Intellij%22) jobs
in [https://github.com/robocorp/robotframework-lsp/actions](https://github.com/robocorp/robotframework-lsp/actions),
then extract the `robotframework-intellij-X.XX.X.zip` from it (due to a limitation in the GitHub upload artifacts
action, even a single .zip is zipped again).

Afterwards, proceed to `File` > `Settings` > `Plugins`, click the `gear` icon, choose `Install Plugin from Disk...`,
point to the `robotframework-intellij-X.XX.X.zip` file and then restart Intellij.

**Note (common on Mac OS)**: if you unzipped and instead of the `robotframework-intellij-X.XX.X.zip` you get
directories, your .zip program is automatically unzipping the .zip inside the `distribution-intellij.zip`. In this case
you can either use a different program to unzip or re-zip those extracted contents into a new .zip.


How to change the file-watch mode?
----------------------------------

By default the language server uses `watchdog` for native file watching on Windows and polling (through `fsnotify`) on
Mac and Linux (because for these using the `watchdog`
library may run out of system resources, in which case those limits may have to be manually raised).

It's possible to change the file-watch mode by setting an environment variable:

`ROBOTFRAMEWORK_LS_WATCH_IMPL` to one of the following values:

- `watchdog`: for native file watching (in this case, please also install the latest `watchdog`
  in your python environment and raise the related limits according to your workspace contents --
  see: https://pythonhosted.org/watchdog/installation.html for more details).

- `fsnotify` for file watching using polling.

After setting the environment variable on your system, please restart the language server client you're using so that it
picks up the new environment variable value.

**Note**: when possible using `watchdog` is recommended.


How to solve (NO_ROBOT) too old for linting?
--------------------------------------------

This means that the Python which is being used doesn't have `Robot Framework` installed.

To fix this, please use a configure a Python executable which does have `Robot Framework`
installed (either through `robot.language-server.python` or `robot.python.executable` 
-- see: [config.md](config.md) for details) or install
`Robot Framework` in the Python that's being used by the language server.


How to configure the launch from a code lens/shortcut?
------------------------------------------------------

To configure the launch from a code lens/shortcut, please create a launch
configuration named `Robot Framework: Launch template` in `.vscode/launch.json`.

i.e.: To configure the terminal to be an `integrated` terminal on all launches
and to specify all launches to have an additional `--argumentfile /path/to/arguments.txt`,
it's possible to create a `.vscode/launch.json` such as:

```
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "robotframework-lsp",
            "name": "Robot Framework: Launch template",
            "request": "launch",
            "terminal": "integrated",
            "args": ["--argumentfile", "/path/to/arguments.txt"]
        }
    ]
}
```

How to use variables in settings?
----------------------------------

Since `Robot Framework Language Server 0.17.0`, the settings may contain variables
in the settings.

The variables available are `${workspace}`, which points to the workspace root or
`${env.ENV_VAR_NAME}`, which will obtain the `ENV_VAR_NAME` from the environment
variables.

Also, since `0.17.0`, it's also possible to prefix a setting value with `~` so that
the user homedir is replaced.

Example:

```
{
  "robot.pythonpath": [
      "~/lib/", 
      "${worskpace}/lib", 
      "${env.MYROOT}/lib"
    ]
}
```


How to debug high-cpu usage in Robot Framework Language Server?
----------------------------------------------------------------

Note: `Robot Framework Language Server 0.17.0` has a bugfix for a case which
could result in high-cpu usage, so, make sure you have the newest version
released prior to reporting an issue.

If even after upgrading you have a Python process with high-cpu related to the
`Robot Framework Language Server`, please create an issue with the related
`pstats` files following the steps provided in 
https://github.com/robocorp/robotframework-lsp/issues/350#issuecomment-842506969 
