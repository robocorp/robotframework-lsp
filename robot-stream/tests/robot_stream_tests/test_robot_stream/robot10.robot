*** Settings ***
Library    String
*** Keywords ***
Some Keyword
    ${value}=    Set Variable    retval
    ${rem}=    Remove String    ${value}    a
    RETURN    ${rem}    ${value}


*** Test Cases ***
Check if
    Some Keyword
