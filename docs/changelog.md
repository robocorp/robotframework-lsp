
New in 0.0.10 (2020-04-28)
-----------------------------

- Code analysis: check if keywords are properly imported/defined (new in 0.0.10).
- Properly consider that keywords may appear in fixtures and templates (code analysis, code completion and go to definition).
- Add `args` placeholder to Robot launch configuration file (launching).
- Arguments are now shown in keyword documentation (code completion).
- Properly deal with path based library imports (code analysis, code completion and go to definition).

New in 0.0.9 (2020-04-20)
-----------------------------

- Go to definition implemented for keywords.
- Only environment variables set by the user when launching are passed when launching in integrated terminal.
- `~` is properly expanded when it's specified in the logging file.

New in 0.0.8 (2020-04-14)
-----------------------------

- Launch robotframework directly from VSCode (note: right now debugging is still not supported 
  -- a debug run will do a regular launch). Fixes [#29](https://github.com/robocorp/robotframework-lsp/issues/29)
- A setting to complete section headers only in the plural/singular form is now available (`robot.completions.section_headers.form`). Fixes [#42](https://github.com/robocorp/robotframework-lsp/issues/42)
- Improvements in syntax highlighting

New in 0.0.7 (2020-04-04)
-----------------------------

- Return empty list when code formatter has no changes. Fixes [#35](https://github.com/robocorp/robotframework-lsp/issues/35)
- Don't show keywords twice. Fixes [#34](https://github.com/robocorp/robotframework-lsp/issues/34)
- Improvements in syntax highlighting


New in 0.0.6 (2020-04-02)
-----------------------------

- Provide source code formatting with the Tidy builtin tool. Fixes [#26](https://github.com/robocorp/robotframework-lsp/issues/26)
- Fix for incomplete json message ([#33](https://github.com/robocorp/robotframework-lsp/issues/33)) and parsing of .resource ([#32](https://github.com/robocorp/robotframework-lsp/issues/32))


New in 0.0.5 (2020-03-30)
-----------------------------

- Add icon to extension. Fixes [#22](https://github.com/robocorp/robotframework-lsp/issues/22)
- Code completion for keywords.
- License is now Apache 2.0. Fixes [#24](https://github.com/robocorp/robotframework-lsp/issues/24)


New in 0.0.4 (2020-03-05)
-----------------------------

- Code completion for section internal names


New in 0.0.3 (2020-02-11)
-----------------------------

- Code completion for section headers


New in 0.0.2 (2020-02-09)
-----------------------------

- Various internal improvementss


New in 0.0.1 (2020-01-31)
-----------------------------

- Basic syntax highlighting
- Syntax validation