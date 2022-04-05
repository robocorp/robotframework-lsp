*** Settings ***
Resource    ./vars_resource.resource
Library   LibWithParams4    ${resolve_this}


*** Test Case ***
Test name
    LibWithParams4.Check