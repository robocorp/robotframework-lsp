*** Settings ***
Variables       variable.py

*** Test Cases ***
TC
    Should Be Equal  ${SUITE}  suite1.subsuite1
    Should Be Equal  ${SUITE 11}  suite1.subsuite1
    Variable Should Not Exist  ${SUITE 1}
#!                               ^^^^^^^ Undefined variable: SUITE 1
    Variable Should Not Exist  ${SUITE 2}
#!                               ^^^^^^^ Undefined variable: SUITE 2
    Variable Should Not Exist  ${SUITE 3}
#!                               ^^^^^^^ Undefined variable: SUITE 3
    Variable Should Not Exist  ${SUITE 31}
#!                               ^^^^^^^^ Undefined variable: SUITE 31
    Variable Should Not Exist  ${SUITE 32}
#!                               ^^^^^^^^ Undefined variable: SUITE 32

