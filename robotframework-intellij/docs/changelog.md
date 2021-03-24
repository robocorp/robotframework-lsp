New in 0.11.0 (2021-03-24)
-----------------------------

- [Intellij] Improved initialization of language server to validate the python executable and ask for a new one if the one found is not valid.
- [Intellij] Fix PYTHONPATH so that the language server shipped in the Intellij plugin is the one used.
- [Intellij] When requesting a completion, cancel previous one requested.
- [Intellij] Language server executable can be project dependent.
- [Robocop](https://robocop.readthedocs.io/en/latest/) is now used to lint (enabled by default, can be disabled in settings).
- Snippets completion is now properly case-insensitive.
- If there's some problem computing semantic tokens, log it and still return a valid value. [#274](https://github.com/robocorp/robotframework-lsp/issues/274)
- If a keyword name is defined in the context, don't try to create an auto-import for it.
- Reworded some settings to be clearer.


New in 0.10.0 (2021-03-19)
-----------------------------

- Fixed issue initializing the language server if there was a space in the installation path.
- Improved coloring is now computed on a thread using the `semanticTokens/full` request.
- Fixed issue applying `FOR` templates.
- Multi-line completions are properly indented when applied.
- `FOR` templates no longer have a `/` in them.
- Added templates for `IF` statements.


New in 0.9.1 (2021-03-20)
-----------------------------

- Handles .resource files. [#251](https://github.com/robocorp/robotframework-lsp/issues/251)
- If some error happens starting up the language server, show more information.
- The settings may now also be set per project and not only globally. [#254](https://github.com/robocorp/robotframework-lsp/issues/254)
- Fix issue getting prefix for filesystem completions. [#256](https://github.com/robocorp/robotframework-lsp/issues/256)
- Support python packages as libraries (package/__init__.py). [#228](https://github.com/robocorp/robotframework-lsp/issues/228)


New in 0.9.0 (2021-03-03)
-----------------------------

- Fixed issue applying arguments completion.
- Code completion for arguments properly brought up if a part of it is still not typed.
- Prefix properly computed for completions. [#248](https://github.com/robocorp/robotframework-lsp/issues/248)
- Completion with dollar sign properly applied. [#249](https://github.com/robocorp/robotframework-lsp/issues/249)
- Gathering workspace symbols is much faster.
- Keyword completions should not be duplicated by the auto-import Keyword completions anymore. 
- It's now possible to use polling instead of native filesystem notifications
  - It may be useful in case watchdog is having glitches.
  - To use it, set an environment variable: `ROBOTFRAMEWORK_LS_WATCH_IMPL=fsnotify`


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