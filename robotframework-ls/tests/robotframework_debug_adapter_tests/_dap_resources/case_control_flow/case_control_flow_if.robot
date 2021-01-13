
*** Keywords ***
My Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Keywords ***
Yet Another Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}
    
*** Variables ***
${counter}    2

*** Test Cases ***
Can use resource keywords
    
    IF    ${counter} > 1    # Break 1
        Log    'Call ${counter} > 0'    console=True
    ELSE
        Log    'Call ${counter} < 0'    console=True
    END
