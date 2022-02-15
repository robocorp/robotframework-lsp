*** Test Cases ***
Debugger Example
    ${data}    ${status}=    Run Keyword And Ignore Error    Keyword Will Fail
    
    
*** Keywords ***
Keyword Will Fail
    [Documentation]    Example of failing keyword
    Fail