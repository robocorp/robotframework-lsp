*** Test Cases ***
Match all allowed
    [Documentation]    FAIL Keyword '\${catch all}' expected 0 arguments, got 1.
    Exact match    hello kitty
#!  ^^^^^^^^^^^ Multiple keywords matching: 'Exact match' in current file.
#!                 ^^^^^^^^^^^ Unexpected argument: hello kitty
    Matches catch all
    Matches catch all    Illegal with argument
#!                       ^^^^^^^^^^^^^^^^^^^^^ Unexpected argument: Illegal with argument

*** Keywords ***
${catch all}
        BuiltIn.Log     x

Exact match
        [Arguments]     ${foo}
        BuiltIn.Log     ${foo}
