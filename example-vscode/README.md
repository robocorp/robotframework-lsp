This project contains a bare-bones project which should be used as a base
to startup a new project based on `robocorp-python-ls-core`.

To create a new project, copy this project and then:

- edit package.json to set proper values 
- edit dev.py so that it references the proper places
- edit .vscodeignore to ignore the proper files
- edit .project to set the proper project name
- edit extension.ts to hear the proper config values
- edit `src/example_vscode/__init__.py` to fix the vendored folder
- create the related test/release workflow in the .github/workflows