*** Settings ***
Resource    case_root.robot

*** Keywords ***
Check with keyword at inner
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Test Cases ***
Testing Completion Here
    Check with ke