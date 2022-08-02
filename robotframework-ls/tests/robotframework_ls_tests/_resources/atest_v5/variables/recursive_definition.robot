*** Settings ***
Test Template     Variable should not exist
Resource          ${IMPORT 1}.robot
#!                ^^^^^^^^^^^ Unable to statically resolve variable: ${IMPORT 1} because dependent variable: ${IMPORT 2} was not resolved.
Library           ${IMPORT 2}.py
#!                ^^^^^^^^^^^ Unresolved library: ${IMPORT 2}.py.
#!                ^^^^^^^^^^^ Unable to statically resolve variable: ${IMPORT 2} because dependent variable: ${IMPORT 1} was not resolved.

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
