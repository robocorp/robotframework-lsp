*** Settings ***
Library           Collections
Library           OperatingSystem    WITH NAME    OS
Resource          ./hover_resource.resource
Variables         ./hover_variables.py
Test Setup        Log    ${TEST NAME}

*** Variables ***
${some var}=      ${22}
${another var}=      %{path}

*** Test Cases ***
T1
    FOR    ${i}    IN    string
        Log    ${i}    console=True
    END
    ${opts}=    Create dictionary    create=True
    ${dct}=    Put Key    key    ${opts}
    Log to console    ${dct}

*** Keywords ***
Put Key
    [Arguments]    ${key}    ${opts}
    IF    $opts.get("create")
        ${ret}=    Create dictionary    ${key}=${some var}
    ELSE
        ${ret}=    Create dictionary
    END
    [Return]    ${ret}
