*** Settings ***
Library    Collections
Resource    ./my_resource.robot

*** Test Cases ***
Some test
    Log To Console    ${some_var}
    Log To Console    ${resource_var}