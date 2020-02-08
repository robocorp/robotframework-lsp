from _pytest.assertion import register_assert_rewrite

register_assert_rewrite("robotframework_ls_tests.language_server_client")

from robotframework_ls import fix_py2
from robotframework_ls.constants import IS_PY2

if IS_PY2:
    fix_py2.fix_py2()
