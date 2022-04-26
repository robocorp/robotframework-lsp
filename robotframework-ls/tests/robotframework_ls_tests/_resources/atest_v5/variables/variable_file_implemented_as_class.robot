*** Settings ***
Variables    PythonClass.py
Variables    DynamicPythonClass.py    hello    world
Variables    InvalidClass.py

*** Test Cases ***
Python Class
    Should Be Equal    ${PYTHON STRING}    hello
#!                       ^^^^^^^^^^^^^ Undefined variable: PYTHON STRING
    Should Be Equal    ${PYTHON INTEGER}    ${42}
#!                       ^^^^^^^^^^^^^^ Undefined variable: PYTHON INTEGER
    Should Be True    ${PYTHON LIST} == ['a', 'b', 'c']
#!                      ^^^^^^^^^^^ Undefined variable: PYTHON LIST

Methods in Python Class Do Not Create Variables
    Variable Should Not Exist    ${python_method}
#!                                 ^^^^^^^^^^^^^ Undefined variable: python_method

Properties in Python Class
    Should Be Equal    ${PYTHON PROPERTY}    value
#!                       ^^^^^^^^^^^^^^^ Undefined variable: PYTHON PROPERTY

Dynamic Python Class
    Should Be Equal    ${DYNAMIC PYTHON STRING}    hello world
#!                       ^^^^^^^^^^^^^^^^^^^^^ Undefined variable: DYNAMIC PYTHON STRING
    Should Be True    @{DYNAMIC PYTHON LIST} == ['hello', 'world']
#!                      ^^^^^^^^^^^^^^^^^^^ Undefined variable: DYNAMIC PYTHON LIST
    Should Be True    ${DYNAMIC PYTHON LIST} == ['hello', 'world']
#!                      ^^^^^^^^^^^^^^^^^^^ Undefined variable: DYNAMIC PYTHON LIST
