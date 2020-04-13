*** Settings ***

Resource    case4resource.txt
Resource    case4resource.txt

*** Test Cases ***
Can use resource keywords
    [Documentation]      Checks that we can have a resource
    ...                  including another resource.
    My Equal Redefined   2   2
    Yet Another Equal Redefined     2   2