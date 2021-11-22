*** Settings ***
Library   LibWithParams    some_param=foo    WITH NAME   Lib

*** Test Case ***
My Test
    Lib.Foo Method