The files in this directory should be downloaded from Python 2.7 (which
is the version which needs most dependencies) by using:

pip install -r requirements.txt --target .

Then:
- rename `backports` to `py2_backports` 
- remove configparser.py
- commit the code

This was done because of conflicts with a base version which could be already 
installed (say, `backports.configparser` was installed but `backports.functools_lru_cache`
was not).

The extension will add the needed requirements to the PYTHONPATH as needed when
it starts up (so, those don't need to be installed at the Python executable
which will run the extension).

Note: when changing requirements.txt, setup.py also needs to be updated. 