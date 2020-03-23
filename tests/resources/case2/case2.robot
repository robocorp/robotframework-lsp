*** Keywords ***
My Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}
    
*** Test Cases ***
User can call library
    My Equal Redefined   1   2