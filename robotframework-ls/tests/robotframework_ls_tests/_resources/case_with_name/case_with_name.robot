*** Settings ***
Library   Collections    WITH NAME   Lib

*** Test Case ***
My Test
    ${dict}=   Create dictionary
    Lib.Set to dictionary    ${dict}    a=10
    settodictionary    ${dict}    b=20
    Log to console    ${dict}
