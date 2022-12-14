*** Settings ***
Library     Collections


*** Test Cases ***
My Test
    ${customer}=    Create list
    WHILE    len($customer)>0
        Collections.Remove from list    ${customer}    0    # Break 1
    END
