*** Keywords ***
Yet Another Equal Redefined
    [Documentation]     Yes, this is redefined.
    ...                 2nd line.
    ...                 3rd line.
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}