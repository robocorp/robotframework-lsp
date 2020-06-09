import pytest
import os
import logging

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


class _CasesFixture(object):
    def __init__(self):
        self.resources_dir = os.path.join(os.path.dirname(__file__), "_resources")
        assert os.path.exists(self.resources_dir)

    def get_path(self, resources_relative_path, must_exist=True):
        path = os.path.join(self.resources_dir, resources_relative_path)
        if must_exist:
            assert os.path.exists(path), "%s does not exist." % (path,)
        return path

    def copy_to(self, case, dest_dir):
        import shutil

        shutil.copytree(self.get_path(case, must_exist=True), dest_dir)


@pytest.fixture(scope="session")
def cases():
    return _CasesFixture()


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
        from robocode_ls_core import uris
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        path = self._cases.get_path(relative_path)
        self._ws = RobotWorkspace(uris.from_fs_path(path), **kwargs)

    def get_doc(self, root_relative_path, create=True):
        from robocode_ls_core import uris

        path = os.path.join(self._ws.root_path, root_relative_path)
        uri = uris.from_fs_path(path)
        return self.ws.get_document(uri, create=create)


@pytest.fixture
def workspace(cases):
    return _WorkspaceFixture(cases)
