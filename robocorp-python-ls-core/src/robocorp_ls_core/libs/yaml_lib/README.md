The files in this directory contain watchdog and the needed deps.

To update, erase it and run:

pip install pyyaml --target .

Then:
- Remove any binary wheels
- commit the code
- Verify if the license brought in from the library is OK

This folder should be automatically added to the PYTHONPATH when needed.