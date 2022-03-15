*** Settings ***
Documentation    Example of using suite variables
Suite Setup         Create Suite Resources

*** Test Cases ***
Test 1
    [Documentation]    Example of suite variable

    Log To Console    ${CONST_1}

Tests Global
    [Documentation]    Example of global variable
    Log To Console    ${GLOBAL_VAR}
    

*** Keywords ***
Create Suite Resources
    [Documentation]    Sets up some suite variables

    Set Suite Variable    ${CONST_1}    foo