Reporting issues
-----------------

To report some issue in the `Robot Framework Language Server`, please create a ticket in 
the [Issue Tracker](https://github.com/robocorp/robotframework-lsp/issues/new).

If it's a bug, please collect the logs so that it's possible to verify what's happening.

To do that it's possible to either:
- Set the `robot.language-server.args` setting to `["-vv", "--log-file=<path/to/robotframework_ls.log>"]` (`Language Server Args` in the Intellij settings).  
- Set an environment variable: `ROBOTFRAMEWORK_LS_LOG_FILE=<path/to/robotframework_ls.log>`.

Note: In `VSCode` it's possible to use `Ctrl+,` to open the user preferences to set some setting.

After it's set, close the client, make sure that `<path/to/>` does not contain any `.log` files and then
open the client again.

Then, reproduce the related issue (which may be as simple as opening a file for code analysis or
doing a code-completion or find definition action), then close the client right afterwards (so that
no other unrelated actions add noise to the log), collect all the `.log` files created
in the specified directory and attach them to the issue.

Note: the language server usually creates multiple log files, one for each process it spawns,
and all of those should be attached.
   
**Important** : After the logs are collected, **remove** (or comment) the `robot.language-server.args` setting 
or unset the `ROBOTFRAMEWORK_LS_LOG_FILE` environment variable to **stop the logging** 
(having the logging on may make the language server go slower). 