Steps to do a new release
--------------------------

To release a new version:

- Open a shell at the proper place (something as `X:\robocorpws\robotframework-lsp\robocorp-code`)

- Create release branch (`git branch -D release-robocorp-code & git checkout -b release-robocorp-code`)

- Update version (`python -m dev set-version 1.22.3`).

- Update README.md to add notes on features/fixes.

- Update changelog.md to add notes on features/fixes and set release date.

- Push contents to release branch, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.
  - `mu acp Release Robocorp Code 1.22.3`

- Rebase with master (`git checkout master & git rebase release-robocorp-code`).

- Create a tag (`git tag robocorp-code-1.22.3`) and push it.
