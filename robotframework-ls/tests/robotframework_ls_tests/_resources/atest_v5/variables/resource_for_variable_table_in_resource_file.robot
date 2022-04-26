*** Variables ***
${STRING}         Hello world!
${INTEGER}        ${42}
${FLOAT}          ${-1.2}
${BOOLEAN}        ${True}
${NONE VALUE}     ${None}
${ESCAPES}        one \\ two \\\\ \${non_existing}
${NO VALUE}       ${EMPTY}
@{ONE ITEM}       Hello again?
@{LIST}           Hello    again    ?
@{LIST WITH ESCAPES}    one \\    two \\\\    three \\\\\\    \${non_existing}
@{LIST CREATED FROM LIST WITH ESCAPES}    @{LIST WITH ESCAPES}
@{EMPTY LIST}
${lowercase}      Variable name in lower case
@{lowercase list}      Variable name in lower case
${S P a c e s }    Variable name with spaces
@{s P a c es L i sT}    Variable name with spaces
${UNDER_scores}    Variable name with under scores
@{_u_n_d_e_r___s_c_o_r_e_s___lis__t_}    Variable name with under scores
${ASSING MARK} =    This syntax works starting from 1.8
@{ASSIGN MARK LIST}=   This syntax works    starting    from    ${1.8}
${THREE DOTS}     ...
@{3DOTS LIST}     ...   ...
${CATENATED}      I    am    a    scalar     catenated     from    many     items
${CATENATED W/ SEP}    SEPARATOR=-    I    can    haz    custom    separator
${NONEX 1}        Creating variable based on ${NON EXISTING} variable fails.
#!                                             ^^^^^^^^^^^^ Undefined variable: NON EXISTING
${NONEX 2A}       This ${NON EX} is used for creating another variable.
#!                       ^^^^^^ Undefined variable: NON EX
${NONEX 2B}       ${NONEX 2A}
${NONEX 3}        This ${NON EXISTING VARIABLE} is used in imports.
#!                       ^^^^^^^^^^^^^^^^^^^^^ Undefined variable: NON EXISTING VARIABLE

*** Settings ***
Resource          ${NONEX 3}
#!                ^^^^^^^^^^ Unresolved resource: ${NONEX 3}
Library           ${NONEX 3}
#!                ^^^^^^^^^^ Unresolved library: ${NONEX 3}.
#!                ^^^^^^^^^^ Error generating libspec:
#!                ^^^^^^^^^^ Importing library 'This ${NON EXISTING VARIABLE} is used in imports.' failed: ModuleNotFoundError: No module named 'This ${NON EXISTING VARIABLE} is used in imports'
#!                ^^^^^^^^^^ Consider adding the needed paths to the "robot.pythonpath" setting
#!                ^^^^^^^^^^ and calling the "Robot Framework: Clear caches and restart" action.
