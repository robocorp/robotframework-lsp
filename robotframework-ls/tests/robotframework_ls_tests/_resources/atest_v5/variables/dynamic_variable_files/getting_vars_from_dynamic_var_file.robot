*** Settings ***
Variables  dyn_vars.py  dict
Variables  dyn_vars.py  mydict
Variables  dyn_vars.py  Mapping
Variables  dyn_vars.py  UserDict
Variables  dyn_vars.py  MyUserDict

*** Test Cases ***
Variables From Dict Should Be Loaded
    Should Be Equal  ${from dict}  This From Dict
#!                     ^^^^^^^^^ Undefined variable: from dict
    Should Be Equal  ${from dict2}  ${2}
#!                     ^^^^^^^^^^ Undefined variable: from dict2

Variables From My Dict Should Be Loaded
    Should Be Equal  ${from my dict}  This From My Dict
#!                     ^^^^^^^^^^^^ Undefined variable: from my dict
    Should Be Equal  ${from my dict2}  ${2}
#!                     ^^^^^^^^^^^^^ Undefined variable: from my dict2

Variables From Mapping Should Be Loaded
    Should Be Equal  ${from Mapping}  This From Mapping
#!                     ^^^^^^^^^^^^ Undefined variable: from Mapping
    Should Be Equal  ${from Mapping2}  ${2}
#!                     ^^^^^^^^^^^^^ Undefined variable: from Mapping2

Variables From UserDict Should Be Loaded
    Should Be Equal  ${from userdict}  This From UserDict
#!                     ^^^^^^^^^^^^^ Undefined variable: from userdict
    Should Be Equal  ${from userdict2}  ${2}
#!                     ^^^^^^^^^^^^^^ Undefined variable: from userdict2

Variables From My UserDict Should Be Loaded
    Should Be Equal  ${from my userdict}  This From MyUserDict
#!                     ^^^^^^^^^^^^^^^^ Undefined variable: from my userdict
    Should Be Equal  ${from my userdict2}  ${2}
#!                     ^^^^^^^^^^^^^^^^^ Undefined variable: from my userdict2
