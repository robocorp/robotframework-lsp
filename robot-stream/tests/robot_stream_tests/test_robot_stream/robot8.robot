*** Test Cases ***
Check if
    ${var1}=    Set Variable    2
    IF    ${var1} == ${var1}
        No Operation
    ELSE IF    ${var1} == ${var1}
        No Operation
    ELSE
        No Operation
    END
