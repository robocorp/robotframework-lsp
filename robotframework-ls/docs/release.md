
Steps to do a new release
---------------------------

- Open a shell at the proper place (something as `X:\robocorpws\robotframework-lsp\robotframework-ls`)

- Create release branch (`git branch -D release-robotframework-lsp&git checkout -b release-robotframework-lsp`)

- Update version (`python -m dev set-version 1.10.0`).

- Update README.md to add notes on features/fixes (on `robotframework-ls` and `robotframework-intellij`).

- Update changelog.md to add notes on features/fixes and set release date (on `robotframework-ls` and `robotframework-intellij`).

- Update build.gradle version and patchPluginXml.changeNotes with the latest changelog (html expected).
  - Use `https://markdowntohtml.com/` to convert the changelog to HTML.

- Push contents, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.
  - `mu acp Robot Framework Language Server Release 1.10.0`

- Rebase with master (`git checkout master&git rebase release-robotframework-lsp`).

- Create a tag (`git tag robotframework-lsp-1.10.0`) and push it.

- Send release msg. i.e.:

Hi @channel,

I'm happy to announce the release of `Robot Framework Language Server 1.10.0`.

### New features

- `robotfamework-output-stream` updated to `0.0.6`. It now has functionality to hide sensitive data.
    See: https://github.com/robocorp/robotframework-output-stream/blob/master/docs/handling_sensitive_data.md
- Variables in variable subscript are now properly found. [#889](https://github.com/robocorp/robotframework-lsp/issues/889)


### Bugfixes

- If the user completes something as `$var`, complete to `${variable}` instead of `$${variable}`.

### Intellij

- Marked as compatible with the latest version of Intellij/ PyCharm.