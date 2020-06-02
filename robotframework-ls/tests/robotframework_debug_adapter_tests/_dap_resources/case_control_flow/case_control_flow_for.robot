
*** Keywords ***
My Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Keywords ***
Yet Another Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Test Cases ***
Can use resource keywords
    FOR    ${counter}    IN RANGE    1    3    # Break 1
        Log    'Call ${counter}'    console=True
    END
    My Equal Redefined   2   2

    Run Keyword If    True    # Break 2
    ...    My Equal Redefined   2   2
    Yet Another Equal Redefined     2   2