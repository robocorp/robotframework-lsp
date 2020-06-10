
*** Keywords ***
My Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}  # Break 1
    Should Be Equal     ${arg1}     ${arg2}

*** Keywords ***
Yet Another Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Test Cases ***
Can use resource keywords
    My Equal Redefined   2   2
    Yet Another Equal Redefined     2   2