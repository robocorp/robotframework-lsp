*** Variables ***
@{EXPECTED LIST}  List  variable  value

*** Test Cases ***
Variables From Variable File
    Should Be Equal  ${SCALAR}  Scalar from variable file from CLI
#!                     ^^^^^^ Undefined variable: SCALAR
    Should Be Equal  ${SCALAR WITH ESCAPES}  1 \\ 2\\\\ \${inv}
#!                     ^^^^^^^^^^^^^^^^^^^ Undefined variable: SCALAR WITH ESCAPES
    Should Be Equal  ${SCALAR LIST}  ${EXPECTED LIST}
#!                     ^^^^^^^^^^^ Undefined variable: SCALAR LIST
    Should Be True  @{LIST} == ${EXPECTED LIST}
#!                    ^^^^ Undefined variable: LIST

Arguments To Variable Files
    Should Be Equal  ${ANOTHER SCALAR}  Variable from CLI var file with get_variables
#!                     ^^^^^^^^^^^^^^ Undefined variable: ANOTHER SCALAR
    Should Be True  @{ANOTHER LIST} == ['List variable from CLI var file', 'with get_variables']
#!                    ^^^^^^^^^^^^ Undefined variable: ANOTHER LIST
    Should Be Equal  ${ARG}  default value
#!                     ^^^ Undefined variable: ARG
    Should Be Equal  ${ARG 2}  value;with;semi;colons
#!                     ^^^^^ Undefined variable: ARG 2

Arguments To Variable Files Using Semicolon Separator
    Should Be Equal  ${SEMICOLON}  separator
#!                     ^^^^^^^^^ Undefined variable: SEMICOLON
    Should Be Equal  ${SEMI:COLON}  separator:with:colons
#!                     ^^^^ Undefined variable: SEMI

Variable File From PYTHONPATH
    Should Be Equal  ${PYTHONPATH VAR 0}  Varfile found from PYTHONPATH
#!                     ^^^^^^^^^^^^^^^^ Undefined variable: PYTHONPATH VAR 0
    Should Be Equal  ${PYTHONPATH ARGS 0}  ${EMPTY}
#!                     ^^^^^^^^^^^^^^^^^ Undefined variable: PYTHONPATH ARGS 0

Variable File From PYTHONPATH with arguments
    Should Be Equal  ${PYTHONPATH VAR 3}  Varfile found from PYTHONPATH
#!                     ^^^^^^^^^^^^^^^^ Undefined variable: PYTHONPATH VAR 3
    Should Be Equal  ${PYTHONPATH ARGS 3}  1-2-3
#!                     ^^^^^^^^^^^^^^^^^ Undefined variable: PYTHONPATH ARGS 3

Variable File From PYTHONPATH as module
    Should Be Equal  ${PYTHONPATH VAR 2}    Varfile found from PYTHONPATH
#!                     ^^^^^^^^^^^^^^^^ Undefined variable: PYTHONPATH VAR 2
    Should Be Equal  ${PYTHONPATH ARGS 2}   as-module
#!                     ^^^^^^^^^^^^^^^^^ Undefined variable: PYTHONPATH ARGS 2

Variable File From PYTHONPATH as submodule
    Should be Equal    ${VARIABLE IN SUBMODULE}    VALUE IN SUBMODULE
#!                       ^^^^^^^^^^^^^^^^^^^^^ Undefined variable: VARIABLE IN SUBMODULE
