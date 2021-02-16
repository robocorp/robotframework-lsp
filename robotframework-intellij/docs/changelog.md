New in 0.8.0 (2021-02-16)
-----------------------------

- Properly consuming stderr from the language server process (redirecting it to `${user.home}/.robotframework-ls/.intellij-rf-ls-XXX.log`).
- Notifying when python cannot be found on the PATH.
- Improved language server startup.
- Added syntax highlighting for variables. 

New in 0.7.2 (2021-02-10)
-----------------------------

- Initial version with support for:
  - Settings for the language server may be set at `File > Settings > Languages & Frameworks > Robot Framework Language Server`
  - Code completion
  - Code analysis
  - Go to definition
  - Browse Keywords (symbols)
  - Syntax highlighting (pretty basic right now)