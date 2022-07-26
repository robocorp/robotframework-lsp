The files in this directory contain watchdog and the needed deps.

To update, erase it and run:

pip install watchdog --target .

Then:
- Remove bin
- commit the code
- Verify if the license brought in from the libraries downloaded are OK
- Make sure that there's a `watchdog_lib/__init__.py` (so that it's added during setup).

Then, go on to:

https://anaconda.org/conda-forge/watchdog/files, download the needed packages and then copy
the `_watchdog_fsevents.xxx.so` to the watchdog_lib.

Then update the permissions of the file:

git update-index --add --chmod=+x _watchdog_fsevents.cpython-38-darwin.so
git update-index --add --chmod=+x _watchdog_fsevents.cpython-39-darwin.so
git update-index --add --chmod=+x _watchdog_fsevents.cpython-310-darwin.so

This folder should be automatically added to the PYTHONPATH when needed.