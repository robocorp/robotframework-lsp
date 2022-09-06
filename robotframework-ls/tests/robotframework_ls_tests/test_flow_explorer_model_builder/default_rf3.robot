*** Settings ***
Library         RPA.Browser.Selenium

*** Variables ***
${LOGIN_STR}    raspberrypi login:
${SERIAL_PORT}  /dev/ttyUSB0
${RPI_IP}       10.0.1.22
${USERNAME}     pi
${PASSWORD}     raspberry
${PROMPT}       pi@raspberrypi:

*** Tasks ***
Main Task
  Main Implemented Keyword
  IF  ${TRUE}
  Main Implemented Keyword
  Comment  This is something grand
  ELSE
  Comment  This is something grand
  Third Implemented Keyword
  END
  Open available browser  https://example.com
  Run Keyword If  '${color}' == 'Red' or '${color}' == 'Blue' or '${color}' == 'Pink'  log to console
  sleep  ${Delay}
  FOR  ${var}  IN  @{VALUES}
    Run Keyword If  '${var}' == 'CONTINUE'  Continue For Loop
    Do Something  ${var}
    sleep  ${Delay}
  END

*** Keywords ***
Main Implemented Keyword
  Comment  This is something grand
  Comment  This is something grand
  Comment  New Keyword
  Second Implemented Keyword

Second Implemented Keyword
  Comment  This is something grand
  Open available browser  https://example.com
  Third Implemented Keyword

Third Implemented Keyword
  Comment  This is something grand
