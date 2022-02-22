
Developing
-----------

Fork the repository at GitHub and then clone the sources of your fork with git.

Get the submodule contents:
`git submodule update --init --recursive`

Install NodeJs (https://nodejs.org/en/) -- make sure that `node` and `npm` are in the `PATH`.

Install Yarn (https://yarnpkg.com/) -- make sure that `yarn` is in the `PATH`.

Install Python and create environment:

In Windows:

```
python -m venv .venv
.venv/Scripts/activate.bat
python -m pip install -r robocorp-code/tests/test_requirements.txt
python -m pip install -r robocorp-code/dev_requirements.txt
python -m pip install robotframework
python -m pip install robotremoteserver
echo %cd%\robotframework-ls\src > .venv\Lib\site-packages\rf_src.pth
echo %cd%\robocorp-code\src >> .venv\Lib\site-packages\rf_src.pth
echo %cd%\robocorp-python-ls-core\src >> .venv\Lib\site-packages\rf_src.pth
echo %cd%\robotframework-ls\tests >> .venv\Lib\site-packages\rf_src.pth
echo %cd%\robocorp-code\tests >> .venv\Lib\site-packages\rf_src.pth
echo %cd%\robocorp-python-ls-core\tests >> .venv\Lib\site-packages\rf_src.pth
```

In Linux:

```
python -m venv .venv
source ./.venv/bin/activate
python -m pip install -r robocorp-code/tests/test_requirements.txt
python -m pip install -r robocorp-code/dev_requirements.txt
python -m pip install robotframework
python -m pip install robotremoteserver
echo $PWD/robotframework-ls/src > .venv/lib/python3.8/site-packages/rf_src.pth
echo $PWD/robocorp-code/src >> .venv/lib/python3.8/site-packages/rf_src.pth
echo $PWD/robocorp-python-ls-core/src >> .venv/lib/python3.8/site-packages/rf_src.pth
echo $PWD/robotframework-ls/tests >> .venv/lib/python3.8/site-packages/rf_src.pth
echo $PWD/robocorp-code/tests >> .venv/lib/python3.8/site-packages/rf_src.pth
echo $PWD/robocorp-python-ls-core/tests >> .venv/lib/python3.8/site-packages/rf_src.pth
```

Head to the root directory (where `package.json` is located) and run: 
`yarn install`.



After this step, it should be possible to open the `roboframework-lsp` folder in VSCode and launch
`Extension: Roboframework-lsp` to have a new instance of VSCode with the loaded extension.


Contributing back
------------------------

After doing the needed work, it's possible to create a pull request.

See: [Creating Pull Request](https://docs.github.com/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) for more details.


Building a VSIX locally
------------------------

To build a VSIX, follow the steps in https://code.visualstudio.com/api/working-with-extensions/publishing-extension
(if everything is setup, `vsce package` from the root directory should do it).

New version release
--------------------

To release a new version:

- Open a shell at the proper place (something as `X:\vscode-robot\robotframework-lsp\robotframework-ls`)

- Create release branch (`git branch -D release-robotframework-lsp&git checkout -b release-robotframework-lsp`)

- Update version (`python -m dev set-version 0.41.0`).

- Update README.md to add notes on features/fixes (on `robotframework-ls` and `robotframework-intellij`).

- Update changelog.md to add notes on features/fixes and set release date (on `robotframework-ls` and `robotframework-intellij`).

- Update build.gradle version and patchPluginXml.changeNotes with the latest changelog (html expected).

- Push contents, get the build in https://github.com/robocorp/robotframework-lsp/actions and install locally to test.

- Rebase with master (`git checkout master&git rebase release-robotframework-lsp`).

- Create a tag (`git tag robotframework-lsp-0.41.0`) and push it.

- Send release msg. i.e.:

Hi @channel, `Robot Framework Language Server 0.41.0` is now available.

Changes in this release:

...

Official clients supported: `VSCode` and `Intellij`.
Other editors supporting language servers can get it with: `pip install robotframework-lsp`.

Install `Robot Framework Language Server` from the respective marketplace or from one of the links below.
Links: [VSCode](https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp), [Intellij](https://plugins.jetbrains.com/plugin/16086-robot-framework-language-server/versions/stable/) , [OpenVSX](https://open-vsx.org/extension/robocorp/robotframework-lsp), [PyPI](https://pypi.org/project/robotframework-lsp/), [GitHub (sources)](https://github.com/robocorp/robotframework-lsp/tree/master/robotframework-ls)