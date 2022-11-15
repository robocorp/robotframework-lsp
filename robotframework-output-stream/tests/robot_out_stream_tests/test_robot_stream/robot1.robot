*** settings ***
Library   Collections
Resource    ./another.robot
Resource    ./sub/another_sub.robot

*** Keywords ***
First keyword
    No operation
    
    Log   Some warning message    level=WARN
    Another keyword
    Another in sub keyword
    
    
*** Tasks ***
Simple Task
    First Keyword
    Log     Some <data &encode </script>
    ${dct}=    Create Dictionary    a=1    b=1
    Log    ${dct}

Check 1
    First Keyword

    FOR    ${counter}    IN RANGE    0    3
        IF    ${counter} == 2
            Fail    Failed execution for some reason...
        END
        Log    ${counter}
    END

Check 2
    ${counter}=    Set Variable    3
    WHILE    ${counter} <= 2
        ${counter}=    Evaluate    $counter-1
        Log    Current counter: ${counter}    level=WARN
    END 
    
Check 3
    TRY
        No Operation
    EXCEPT    message
        No Operation
    FINALLY
        No Operation
    END