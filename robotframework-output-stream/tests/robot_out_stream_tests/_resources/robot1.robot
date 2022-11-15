*** settings ***
Library   Collections

*** Tasks ***
Simple Task
    Log     áéíóú <data &encode </script>
    ${dct}=    Create Dictionary    a=1    b=1
    Log    ${dct}
    FOR    ${counter}    IN RANGE    0    10
        Log    ${counter}
        
    END

