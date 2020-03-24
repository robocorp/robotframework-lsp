*** Settings ***

Resource    case3resource.resource
Resource    ${ext_folder}/case3resource_in_ext.resource

*** Test Cases ***
Can use resource keywords
    My Equal Redefined   2   2
    Yet Another Equal Redefined     2   2