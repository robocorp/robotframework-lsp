*** Test Cases ***
Test case 1
    TRY
        ${SOMETHING}=    Evaluate    5
        WHILE  $SOMETHING > 2
            ${SOMETHING}=    Evaluate    $SOMETHING-1
            Log to console    Something is now: ${SOMETHING}
        END
        Fail    Message
    EXCEPT  Message
        Log to console    Something else
    END