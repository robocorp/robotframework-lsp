*** Settings ***
Documentation    Example of using suite variables
Suite Setup         Create Suite Resources

*** Keywords ***
Create Suite Resources
    [Documentation]    Sets up some global variables

    Set Global Variable    ${GLOBAL_VAR}    bar