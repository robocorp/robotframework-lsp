*** Test Cases ***
Test case 1
    TRY
        Fail    Message
    EXCEPT  Message
        Log to console    On except
    FINALLY
        Log to console    On finally
    END