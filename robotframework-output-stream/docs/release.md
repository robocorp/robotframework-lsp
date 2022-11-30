
Steps to do a new release
---------------------------

- Open a shell at the proper place (something as `X:\vscode-robot\robotframework-lsp\robotframework-output-stream`)

- Create release branch (`git branch -D release-robotframework-output-stream&git checkout -b release-robotframework-output-stream`)

- When leaving pre-alpha: Update classifier in setup.py (currently in pre-alpha) and notes regarding being alpha in README.md.

- Update version (`python -m dev set-version 0.0.2`).

- Update README.md to add notes on features/fixes (on `robotframework-output-stream`).

- Update changelog.md to add notes on features/fixes and set release date.

- Push contents, and check if tests passed in https://github.com/robocorp/robotframework-lsp/actions.
  - `mu acp Robot Framework Output Stream Release 0.0.2`

- Rebase with master (`git checkout master&git rebase release-robotframework-output-stream`).

- Create a tag (`git tag robotframework-output-stream-0.0.2`) and push it.

- Send release msg. i.e.:

Hi @channel,

I'm happy to announce the release of `Robot Framework Output Stream 0.0.2`.

*## Changes*


`Robot Framework Output Stream` may be installed with: `pip install robotframework-output-stream`.
Links: [PyPI](https://pypi.org/project/robotframework-output-stream/), [GitHub (sources)](https://github.com/robocorp/robotframework-lsp/tree/master/robotframework-output-stream)