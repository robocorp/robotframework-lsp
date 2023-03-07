*** Settings ***
Library    RFDebugAdapter

*** Test Cases ***
Connect debugger
    Debug Connect   host=${host}    port=${port}
    
    # Should pause in the next line by default.
    Log    Something
    