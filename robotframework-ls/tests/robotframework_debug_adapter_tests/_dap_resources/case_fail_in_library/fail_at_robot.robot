*** Settings ***
Library     ./my_library.py


*** Test Cases ***
My Test
    my task 222


*** Keywords ***
My task ${something}
    Log    ${something}
    Log to console    message
    Fail here
