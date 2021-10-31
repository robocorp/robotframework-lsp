pydevd is vendored for distribution with the Robot Framework Language Server.

This is done by using a git submodule.

To update, go into the `vendored_pydevd` folder and pull the latest contents and then
go to `robotframework-ls` and commit.


To checkout the contents on cloned repository:
`git submodule update --init --recursive`