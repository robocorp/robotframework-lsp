*** Settings ***
Variables       variable.py

*** Test Cases ***
TC
    Should Be Equal  ${SUITE}  suite3.subsuite1
    Should Be Equal  ${SUITE 31}  suite3.subsuite1
    Variable Should Not Exist  ${SUITE 1}
#!                               ^^^^^^^ Undefined variable: SUITE 1
    Variable Should Not Exist  ${SUITE 11}
#!                               ^^^^^^^^ Undefined variable: SUITE 11
    Variable Should Not Exist  ${SUITE 2}
#!                               ^^^^^^^ Undefined variable: SUITE 2
    Variable Should Not Exist  ${SUITE 3}
#!                               ^^^^^^^ Undefined variable: SUITE 3
    Variable Should Not Exist  ${SUITE 32}
#!                               ^^^^^^^^ Undefined variable: SUITE 32

