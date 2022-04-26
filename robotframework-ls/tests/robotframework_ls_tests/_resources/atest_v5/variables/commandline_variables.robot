*** Test Case ***
Normal Text
    Should Be Equal    ${NORMAL TEXT}    Hello
#!                       ^^^^^^^^^^^ Undefined variable: NORMAL TEXT

Special Characters
    Should Be Equal    ${SPECIAL}    I'll take spam & eggs!!
#!                       ^^^^^^^ Undefined variable: SPECIAL
    Should Be Equal    ${SPECIAL 2}    \${notvar}
#!                       ^^^^^^^^^ Undefined variable: SPECIAL 2

No Colon In Variable
    Should Be Equal    ${NO COLON}    ${EMPTY}
#!                       ^^^^^^^^ Undefined variable: NO COLON
