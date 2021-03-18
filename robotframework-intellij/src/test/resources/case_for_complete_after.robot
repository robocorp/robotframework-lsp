*** Keywords ***
Some keyword
    FOR    ${index}    ${element}    IN ENUMERATE    @{LIST}
        Log    ${index}: ${element}
         
    END