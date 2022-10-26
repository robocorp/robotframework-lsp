*** Settings ***
Library     lib_not_there.py

*** Keywords ***
Another in sub keyword
    No Operation
    Log   Some error message    level=ERROR