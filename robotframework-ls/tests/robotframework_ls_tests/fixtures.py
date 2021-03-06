# coding: utf-8
import pytest
import os
import logging
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture

__file__ = os.path.abspath(__file__)  # @ReservedAssignment


log = logging.getLogger(__name__)


LIBSPEC_1 = """<?xml version="1.0" encoding="UTF-8"?>
<keywordspec name="case1_library" type="library" format="ROBOT" generated="20200316 10:45:35">
<version></version>
<scope>global</scope>
<namedargs>yes</namedargs>
<doc>Documentation for library ``case1_library``.</doc>
<kw name="new Verify Another Model">
<arguments>
<arg>new model=10</arg>
</arguments>
<doc></doc>
<tags>
</tags>
</kw>
<kw name="New Verify Model">
<arguments>
<arg>new model</arg>
</arguments>
<doc>:type new_model: int</doc>
<tags>
</tags>
</kw>
</keywordspec>
"""

LIBSPEC_2 = """<?xml version="1.0" encoding="UTF-8"?>
<keywordspec name="case2_library" type="library" format="ROBOT" generated="20200316 10:45:35">
<version></version>
<scope>global</scope>
<namedargs>yes</namedargs>
<doc>Documentation for library ``case2_library``.</doc>
<kw name="Case 2 Verify Another Model">
<arguments>
<arg>new model=10</arg>
</arguments>
<doc></doc>
<tags>
</tags>
</kw>
<kw name="Case 2 Verify Model">
<arguments>
<arg>new model</arg>
</arguments>
<doc>:type new_model: int</doc>
<tags>
</tags>
</kw>
</keywordspec>
"""

LIBSPEC_2_A = """<?xml version="1.0" encoding="UTF-8"?>
<keywordspec name="case2_library" type="library" format="ROBOT" generated="20200316 10:45:35">
<version></version>
<scope>global</scope>
<namedargs>yes</namedargs>
<doc>Documentation for library ``case2_library``.</doc>
<kw name="Case 2 A Verify Another Model">
<arguments>
<arg>new model=10</arg>
</arguments>
<doc></doc>
<tags>
</tags>
</kw>
<kw name="Case 2 A Verify Model">
<arguments>
<arg>new model</arg>
</arguments>
<doc>:type new_model: int</doc>
<tags>
</tags>
</kw>
</keywordspec>
"""

LIBSPEC_3 = """<?xml version="1.0" encoding="UTF-8"?>
<keywordspec name="case3_library" type="library" format="ROBOT" generated="20200316 10:45:35">
<version></version>
<scope>global</scope>
<namedargs>yes</namedargs>
<doc>Documentation for library ``case3_library``.</doc>
<kw name="Case Verify Typing">
<arguments>
<arg>new model:NoneType=10</arg>
</arguments>
<doc></doc>
<tags>
</tags>
</kw>
</keywordspec>
"""


@pytest.fixture
def language_server_client_class():
    from robocorp_ls_core.unittest_tools.language_server_client import (
        LanguageServerClient,
    )

    return LanguageServerClient


@pytest.fixture
def language_server_class():
    from robotframework_ls.robotframework_ls_impl import RobotFrameworkLanguageServer

    return RobotFrameworkLanguageServer


@pytest.fixture
def main_module():
    from robotframework_ls import __main__

    return __main__


@pytest.fixture(autouse=True, scope="session")
def sync_builtins(tmpdir_factory, cases):
    """
    Pre-generate the builtins.
    """
    from robotframework_ls.impl.libspec_manager import LibspecManager
    import shutil

    user_home = str(tmpdir_factory.mktemp("ls_user_home"))
    os.environ["ROBOTFRAMEWORK_LS_USER_HOME"] = user_home
    internal_libspec_dir = LibspecManager.get_internal_builtins_libspec_dir()
    try:
        os.makedirs(internal_libspec_dir)
    except:
        # Ignore exception if it's already created.
        pass

    builtin_libs = cases.get_path("builtin_libs")

    # Uncomment the line to regenerate the libspec files for the builtin libraries.
    # LibspecManager(builtin_libspec_dir=builtin_libs)

    # Note: use private copy instead of re-creating because it's one of the
    # slowest things when starting test cases.
    # Locally it's the difference from the test suite taking 15 or 25 seconds
    # (with tests with 12 cpus in parallel).

    for name in os.listdir(builtin_libs):
        shutil.copyfile(
            os.path.join(builtin_libs, name), os.path.join(internal_libspec_dir, name)
        )


@pytest.fixture
def libspec_manager(tmpdir):
    from robotframework_ls.impl.libspec_manager import LibspecManager

    libspec_manager = LibspecManager(user_libspec_dir=str(tmpdir.join("user_libspec")))
    yield libspec_manager
    libspec_manager.dispose()


@pytest.fixture(scope="session")
def cases(tmpdir_factory) -> CasesFixture:
    basename = "res áéíóú"
    copy_to = str(tmpdir_factory.mktemp(basename))

    f = __file__
    original_resources_dir = os.path.join(os.path.dirname(f), "_resources")
    assert os.path.exists(original_resources_dir)

    return CasesFixture(copy_to, original_resources_dir)


class _WorkspaceFixture(object):
    def __init__(self, cases):
        self._cases = cases
        self._ws = None

    @property
    def ws(self):
        if self._ws is None:
            raise AssertionError(
                "set_root must be called prior to using the workspace."
            )
        return self._ws

    def set_root(self, relative_path, **kwargs):
        path = self._cases.get_path(relative_path)
        self.set_absolute_path_root(path, **kwargs)

    def set_absolute_path_root(self, path, **kwargs):
        from robocorp_ls_core import uris
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        self._ws = RobotWorkspace(uris.from_fs_path(path), **kwargs)

    def get_doc(self, root_relative_path, accept_from_file=True):
        from robocorp_ls_core import uris

        path = os.path.join(self._ws.root_path, root_relative_path)
        uri = uris.from_fs_path(path)
        return self.ws.get_document(uri, accept_from_file=accept_from_file)


@pytest.fixture
def workspace(cases):
    return _WorkspaceFixture(cases)


@pytest.fixture
def workspace_dir(tmpdir):
    parent = str(tmpdir)
    basename = "ws áéíóú"
    return os.path.join(parent, basename)
