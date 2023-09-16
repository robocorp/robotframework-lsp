The files in this directory contain robotframework-tidy and the needed deps.

To update on python 3.8:

See the deps in https://github.com/MarketSquare/robotframework-tidy/blob/main/setup.py and
install those (removing `rich_click`, `robotframework` and `colorama`)

pip install robotframework-tidy --target . --no-deps
pip install "click==8.1.*" --target .
pip install "pathspec>=0.9.0,<0.11.3" --target .
pip install "tomli==2.0.*" --target .
pip install "jinja2>=3.0,<4.0" --target .

Then:
- remove bin
- remove robot framework
- commit the code
- Verify if the license brought in from the libraries downloaded are OK


This folder should be automatically added to the PYTHONPATH when needed.