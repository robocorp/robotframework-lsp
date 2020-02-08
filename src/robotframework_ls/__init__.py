from robotframework_ls import fix_py2
from robotframework_ls.constants import IS_PY2

if IS_PY2:
    fix_py2.fix_py2()
