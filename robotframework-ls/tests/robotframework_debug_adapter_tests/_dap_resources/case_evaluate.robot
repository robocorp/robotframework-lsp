
*** Settings ***
Library           OperatingSystem

*** Keywords ***
My Equal Redefined
    [Arguments]    ${arg1}    ${arg2}
    Should Be Equal    ${arg1}    ${arg2}
    Should Be Equal    ${arg1}    ${arg2}    # Break 1

Yet Another Equal Redefined
    [Arguments]    @{arg1}
    Should Be Equal    ${arg1}[0]    ${arg1}[0]    # Break 2

Check Call
    [Arguments]    ${arg0}
    My Equal Redefined    ${arg0}    ${arg0}

*** Test Cases ***
Can use resource keywords
    Check Call    2
    Yet Another Equal Redefined    2    2
