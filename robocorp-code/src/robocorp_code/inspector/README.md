The idea is that the available inspectors should be integrated into VSCode.

The architecture proposed for that is the following:

1. /robocorp-code/vscode-client/templates/inspector.html

    Should contain a react app which will provide a webview to work with inspectors.

2. /robocorp-code/src/robocorp_code/inspector (python package)

    Should contain the actual code to control the inspector. 
    
    Example: When the user presses the `pick` button an event is sent from the webview
    and then a handler in `robocorp_code/inspector` will actually handle it.
    
    The idea is that the handling of such commands will be done in a subprocess
    (that subprocess is responsible for actually starting the browser, injecting
    javascript in it and communicating as needed).
    
    The actual communication with that process should happen using the same
    format as the language server protocol (but with custom messages).
