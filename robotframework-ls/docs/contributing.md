Contributing to the Robot Framework Language Server (RFLS)
============================================================

First, thank you! Robot Framework Language Server welcomes anyone wishing to
contribute to the project ;)

What to work on?
==================

To start contributing usually the first step would be choosing what you'd like
to work on, usually one of the issues from: https://github.com/robocorp/robotframework-lsp/issues.
If what you want to work on isn't there, feel free to create an issue for what
you'd like to do and state in the issue that you'd like to provide a pull request
(to avoid possible work duplication from 2 people working at the same thing).

After deciding what you what to work on, it's time to get the code and
bootstrap your development environment.

Code/environment
==================

Fork the repository at GitHub (https://github.com/robocorp/robotframework-lsp)
and then clone the sources of your fork with git to your local machine.

After getting the code, the following steps are needed:

- Get git submodules:

    `git submodule update --init --recursive`


- Install NodeJs (https://nodejs.org/en/) -- make sure that `node` and `npm` are in the `PATH`.

- Install Yarn (https://yarnpkg.com/) -- make sure that `yarn` is in the `PATH`.

- Install Python and create environment:

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
===========================

After doing the code changes, it's possible to create a pull request.

See: [Creating Pull Request](https://docs.github.com/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) for more details.


Codebase style/guidelines
===========================

Please take into account the following guidelines of the `Robot Framework Language Server` codebase:

- The codebase follows a [TDD](https://en.wikipedia.org/wiki/Test-driven_development) style and all code added must be added with the related tests.
- Imports should be local (and not top-level) whenever possible in the `Robot Framework Language Server` codebase
  (so, unless it's a really common import across the whole codebase or something required to be top-level
  -- such as typing -- it should be local).
- Typing: most of the typing should be done through protocols and not nominal typing (see the `protocols.py` across the codebase).
- Typing for the language server specification is done at: `robocorp_ls_core.lsp`.
- Classes that are intended to implement some protocol should use `robocorp_ls_core.protocols.check_implements`
  (see docstrings on that function on how to use it).
- Features should be self contained (so, for instance,  document symbols is in `document_symbol.py` and
  semantic highlighting is in `semantic_highlighting.py`). Unless a feature really becomes huge
  (such as code-completion), most of the code should reside in the same module and functions are usually
  preferred over classes -- but not always ;).
- `robotframework_ls.robotframework_ls_impl.RobotFrameworkLanguageServer` is just a facade to distribute requests
  and it shouldn't import `robot` anywhere. Rather it forwards requests to `robotframework_ls.server_api.server.RobotFrameworkServerApi`
  which is running in another process (which can then import the module that actually implements the request, which can import `robot`).
- Remember that the `package.json` is generated from `codegen/codegen_package.py`.

Third-party libraries
---------------------------

- Third-party libraries must be vendored as it can't be relied that they'll be installed at the client (so, the license must be compatible).
- If a third party-library is vendored or some code is copied from anywhere, make sure to add it to the `ThirdPartyNotices.txt` in the repository
  root and to add the proper headers if it was copied code.


Formatting / type checking
---------------------------

- Code is formatted with [black](https://github.com/psf/black/), with the version found in `dev_requirements.txt`.
- Code is type-checked with [mypy](http://mypy-lang.org/), with the version found in `dev_requirements.txt`.
    - Keep in mind that the code is type-checked in `Python 3.8` but it needs to run in `Python 3.7+`.
- Github Actions are used to run the tests and make sure that formatting/type checking works.


Building a VSIX locally
===========================

To build a VSIX, follow the steps in https://code.visualstudio.com/api/working-with-extensions/publishing-extension
(if everything is setup, `vsce package` from the root directory should do it).
