*** Settings ***
Variables     var_in_init

*** Test Cases ***
User can call library
    Log to console    ${var_in_init}