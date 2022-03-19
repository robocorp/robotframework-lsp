*** Settings ***
Resource    case_vars_file_yml.resource


*** Test Cases ***
Test
    Log    ${VARIABLE_YAML_2}    console=True
    Log    ${Var|in.Resource}    console=True