*** Settings ***
Library         RPA.Browser.Selenium

*** Tasks ***
Main Task
  Main Implemented Keyword
  IF  ${var1} == ${var1}
  Main Implemented Keyword
  ELSE
  Comment  This is something grand
  Third Implemented Keyword
  END
  Open available browser  https://example.com

*** Keywords ***
Main Implemented Keyword
  Comment  This is something grand
  Comment  This is something less grand
  Comment  New Keyword
  Second Implemented Keyword

Second Implemented Keyword
  Comment  This is something grand
  Open available browser  https://example.com
  Third Implemented Keyword

Third Implemented Keyword
  Comment  This is something grand
