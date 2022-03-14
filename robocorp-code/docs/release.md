Steps to do a new release
--------------------------

To release a new version:

- Open a shell at the proper place (something as `X:\vscode-robot\robotframework-lsp\robocorp-code`)

- Create release branch (`git branch -D release-robocorp-code&git checkout -b release-robocorp-code`)

- Update version (`python -m dev set-version 0.28.0`).

- Update README.md to add notes on features/fixes.

- Update changelog.md to add notes on features/fixes and set release date.

- Push contents to release branch, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.

- Rebase with master (`git checkout master&git rebase release-robocorp-code`).

- Create a tag (`git tag robocorp-code-0.28.0`) and push it.
