
def _add_to_sys_path():
    import sys
    from os.path import os
    libs_py2_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs_py2")
    if not os.path.exists(libs_py2_dir):
        raise AssertionError('Expected: %s to exist.' % (libs_py2_dir,))
    sys.path.append(libs_py2_dir)

def fix_py2():
    from robotframework_ls.constants import IS_PY2
    if IS_PY2:
        # On Py2 we automatically put the needed deps on the PYTHONPATH.
        _add_to_sys_path()
        
        # Check that it worked.
        from py2_backports import configparser
        from py2_backports.functools_lru_cache import lru_cache
