*** Test Cases ***
Check while
    ${a}=    Evaluate    2
    WHILE    $a < 1
        ${a}=    Evaluate    $a-1
    END