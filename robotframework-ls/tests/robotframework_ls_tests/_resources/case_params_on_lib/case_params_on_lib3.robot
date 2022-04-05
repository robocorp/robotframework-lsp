*** Settings ***
Library   LibWithParams3    ${resolve_this}


*** Variables ***
${resolve_this}=    RESOLVED

*** Test Case ***
Test name
    LibWithParams3.Check