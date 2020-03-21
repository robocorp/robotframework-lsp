The files in this directory should be downloaded from Python 2.7 (which
is the version which needs most dependencies) by using:

pip install -r requirements.txt --target .

Then:
- rename `backports` to `py2_backports` 
- remove configparser.py
- fix imports to conform to its current location in the PYTHONPATH
- commit the code

This was done because of conflicts with a base version which could be already 
installed (say, `backports.configparser` was installed but `backports.functools_lru_cache`
was not).

The code will import the modules as `from robotframework_ls.libs_py2.py2_backports import ...`