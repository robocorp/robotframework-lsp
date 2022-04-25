*** Test Cases ***
Match all allowed
    [Documentation]    FAIL Keyword '\${catch all}' expected 0 arguments, got 1.
    Exact match    hello kitty
    Matches catch all
    Matches catch all    Illegal with argument
#!                       ^^^^^^^^^^^^^^^^^^^^^ Unexpected argument: Illegal with argument

*** Keywords ***
${catch all}
        BuiltIn.Log     x
#!                      ^ Unexpected argument: x

Exact match
        [Arguments]     ${foo}
        BuiltIn.Log     ${foo}
#!                      ^^^^^^ Unexpected argument: ${foo}
