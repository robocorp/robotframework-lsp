
*** Settings ***
Suite Setup    Log    SuiteSetup    console=True
Test Setup    Log    TestSetup    console=True
Test Teardown    Log    TestTeardown    console=True
Suite Teardown    Log    SuiteTeardown    console=True

*** Test Cases ***
Test
    Log To Console    TestStep
