*** Settings ***
Test Template     Variable should not exist
Resource          ${IMPORT 1}.robot
#!                ^^^^^^^^^^^^^^^^^ Unresolved resource: ${IMPORT 1}.robot
#!                ^^^^^^^^^^^^^^^^^ Note: resolved name: ${IMPORT 2}.robot
Library           ${IMPORT 2}.py
#!                ^^^^^^^^^^^^^^ Unresolved library: ${IMPORT 2}.py.
#!                ^^^^^^^^^^^^^^ Error generating libspec:
#!                ^^^^^^^^^^^^^^ Importing library '${IMPORT 1}' failed: ModuleNotFoundError: No module named '${IMPORT 1}'
#!                ^^^^^^^^^^^^^^ Note: resolved name: ${IMPORT 1}.py
#!                ^^^^^^^^^^^^^^ Consider adding the needed paths to the "robot.pythonpath" setting
#!                ^^^^^^^^^^^^^^ and calling the "Robot Framework: Clear caches and restart" action.

*** Variables ***
${DIRECT}         ${DIRECT}
${VAR 1}          ${VAR 2}
${VAR 2}          ${VAR 3}
${VAR 3}          ${VAR 1}
${xxx}            ${X X X}
@{LIST}           @{list}
@{LIST 1}         @{LIST 2}
@{LIST 2}         Hello    @{LIST 1}
${IMPORT 1}       ${IMPORT 2}
${IMPORT 2}       ${IMPORT 1}

*** Test Cases ***
Direct recursion
    ${DIRECT}

Indirect recursion
    ${VAR 1}
    ${VAR 2}
    ${VAR 3}

Case-insensitive recursion
    ${xxx}

Recursive list variable
    @{LIST}
    @{LIST 1}
    @{LIST 2}

Recursion with variables used in imports
    ${IMPORT 1}
    ${IMPORT 2}
