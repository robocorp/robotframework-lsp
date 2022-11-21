*** Settings ***
Documentation       Tests for the Output View.

Library             RPA.Browser.Playwright
Library             String
Library             json
Library             RPA.FileSystem
Library             Collections
Library             ./uris.py

Test Teardown       Close Browser


*** Variables ***
# ${HEADLESS}     False
${HEADLESS}    True


*** Test Cases ***
Test Scenario 1
    [Documentation]
    ...    A simple scenario where the output view is opened with a
    ...    single test which passed without any keywords.
    Open Output View For Tests
    Setup Scenario    ${CURDIR}/_resources/case1.rfstream
    Check Labels    1
    Check Tree Items Text    Robot1.Simple Task

Test Scenario 2
    [Documentation]
    ...    A simple scenario where the output view is opened with a
    ...    single test which passed without any keywords.
    Open Output View For Tests
    Setup Scenario    ${CURDIR}/_resources/case2.rfstream
    Check Labels    1
    Check Tree Items Text    Robot1.Simple Task


*** Keywords ***
Check Integers Equal
    [Arguments]    ${a}    ${b}
    ${a}=    Convert To Integer    ${a}
    ${b}=    Convert To Integer    ${b}
    Builtin.Should Be Equal    ${a}    ${b}

Open Output View For Tests
    ${curdir_proper_slashes}=    Replace String    ${CURDIR}    \\    /
    ${filepath}=    Set Variable    ${curdir_proper_slashes}/../dist-test/index.html
    ${exists}=    RPA.FileSystem.Does File Exist    ${filepath}
    Should Be True    ${exists}

    ${fileuri}=    uris.From Fs Path    ${filepath}
    RPA.Browser.Playwright.Set Browser Timeout    3
    Log To Console    fileuri=${fileuri}
    Open Browser    url=${fileuri}    headless=${HEADLESS}

Setup Scenario
    [Arguments]    ${filename}
    ${contents}=    RPA.FileSystem.Read File    ${filename}
    ${contents_as_json}=    json.Dumps    ${contents}

    Evaluate JavaScript    ${None}
    ...    ()=>{
    ...    window['setupScenario'](${contents_as_json});
    ...    }

Get Text From Tree Items
    ${lst}=    Builtin.Create List
    ${elements}=    RPA.Browser.Playwright.Get Elements    .span_link
    FOR    ${element}    IN    @{elements}
        ${txt}=    RPA.Browser.Playwright.Get Text    ${element}
        Append To List    ${lst}    ${txt}
    END
    RETURN    ${lst}

Check Labels
    [Arguments]    ${expected_number_of_labels}
    ${element_count}=    RPA.Browser.Playwright.Get Element Count    .label
    Check Integers Equal    ${expected_number_of_labels}    ${element_count}

Check Tree Items Text
    [Arguments]    @{expected_text_items}
    ${text_items}=    Get Text From Tree Items
    Should Be Equal    ${text_items}    ${expected_text_items}
