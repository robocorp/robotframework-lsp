Robot Framework Language Server FAQ
======================================

Keywords from a library are not being resolved
-----------------------------------------------

The most common reason this happens is because some error happened when trying to
automatically generate the libspec for a given library.

If you're in `VSCode`, the error may be seen in the `OUTPUT` tab, selecting `Robot Framework` in the dropdown.

For `Intellij`, it's possible to enable logging by setting `["-vv", "--log-file=<path/to/robotframework_ls.log>"]`
(properly replacing the `<path/to>` to some local path in your machine) in the `Language Server Args` in the 
`Robot Framework` settings and then checking the log files generated (look for `EXCEPTION` in the log files). 

**Important**: After the logs are collected, revert the changes to stop the logging 
(having the logging on may make the language server go slower).

The common errors here are:

**1. The library requires arguments to be initialized**

  In this case there are 2 different approaches that can be used:
  
  **a.** Change the library to have default arguments so that libspec can generate it out of the box.

    After the library is changed to accept default arguments, you may need to restart your editor/IDE to clear the related caches.
  
  **b.** Manually generate the libspec for the library and put it somewhere in your workspace or right below a folder in the `PYTHONPATH`.

    It is possible to manually generate a libspec by executing something as:
    
    `python -m robot.libdoc <library_name> <library_name.libspec>`
    
    Notes:
    
      - `-a` may be used to specify an argument
      - In RobotFramework 3.x `--format XML:HTML` must also be passed)
      - See `python -m robot.libdoc -h` for more details
    
    Whenever the library changes, make sure you manually regenerate the libspec.
  
**2. The library is not present in the python executable you're using.**

  In this case, install the library in the given python executable or choose a different python executable
  which has the library installed.


Some library or resource import requires a variable to resolve
---------------------------------------------------------------

In this case, the full path needed to resolve the variable needs to be
specified in a variable in `robot.variables` (relative paths or paths requiring other variables
aren't currently supported). 

i.e.: Given a resource import such as: `Resource ${some_variable}/my.resource`,
`robot.variables` must be set to `{"some_variable": "c:/my/project/src"}`.

  
