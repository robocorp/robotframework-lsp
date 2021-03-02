*** Keywords ***
Some Keyword With Args
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Test Cases ***
Some Test Case
    Some Keyword With Args    $arg1    $arg2