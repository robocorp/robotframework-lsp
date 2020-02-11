from robotframework_ls import fix_py2
from robotframework_ls.constants import IS_PY2

if IS_PY2:
    fix_py2.fix_py2()

__version__ = "0.0.3"
version_info = [int(x) for x in __version__.split(".")]
