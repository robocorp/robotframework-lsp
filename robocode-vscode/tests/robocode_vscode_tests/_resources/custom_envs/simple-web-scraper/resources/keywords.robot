*** Settings ***
Library           ExampleLibrary
Library           OperatingSystem
Variables         variables.py

*** Keyword ***
Store web page content
    ${current_date}=    Current date
    Log    ${current_date}
    Log    ${URL}
    Set Local Variable    ${text}    ${URL}
    Create File    output/text.txt    ${text}
