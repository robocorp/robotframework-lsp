*** Settings ***
Variables    ./robotvars_cls.py


*** Test Cases ***
Test
    Log    ${MyVars}    console=True
    Log    ${MyVars.const1}    console=True