*** Settings ***
Library           case1_library

*** Test Cases ***
User can call library
    verify model   1
    verify_another_model   2