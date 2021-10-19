The files in this directory contain watchdog and the needed deps.

To update, erase it and run (note: using 0.10.3 due to https://github.com/gorakhargosh/watchdog/issues/706 in 0.10.4):

pip install watchdog==0.10.3 --target .

Then:
- Remove bin
- commit the code
- Verify if the license brought in from the libraries downloaded are OK

Then, go on to:

https://anaconda.org/conda-forge/watchdog/files, download the needed packages and then copy
the `_watchdog_fsevents.xxx.so` to the watchdog_lib.

Then update the permissions of the file:

git update-index --add --chmod=+x _watchdog_fsevents.cpython-37m-darwin.so
git update-index --add --chmod=+x _watchdog_fsevents.cpython-38-darwin.so
git update-index --add --chmod=+x _watchdog_fsevents.cpython-39-darwin.so

This folder should be automatically added to the PYTHONPATH when needed.