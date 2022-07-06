*** Settings ***
Variables     variables.var_in_pythonpath

*** Test Cases ***
User can call library
    Log to console    ${var_in_pythonpath}