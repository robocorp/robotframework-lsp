*** Settings ***
Library    OperatingSystem

*** Test Cases ***
Test
    Log to console   RPA_OUTPUT_WORKITEM_PATH: %{RPA_OUTPUT_WORKITEM_PATH}
    Log to console   RPA_INPUT_WORKITEM_PATH: %{RPA_INPUT_WORKITEM_PATH}
    Log to console   RPA_WORKITEMS_ADAPTER: %{RPA_WORKITEMS_ADAPTER}
    Log to console   SOME_OTHER_VAR: %{SOME_OTHER_VAR}
