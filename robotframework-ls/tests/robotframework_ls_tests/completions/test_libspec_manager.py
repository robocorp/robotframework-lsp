import os
from pathlib import Path
from typing import Optional


def test_libspec_info(libspec_manager, tmpdir):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc

    assert "BuiltIn" in libspec_manager.get_library_names()
    lib_info = libspec_manager.get_library_info("BuiltIn", create=False)
    assert isinstance(lib_info, LibraryDoc)
    assert lib_info.source is not None
    assert lib_info.source.endswith("BuiltIn.py")
    for keyword in lib_info.keywords:
        assert isinstance(keyword, KeywordDoc)
        assert keyword.lineno > 0


def arg_to_dict(arg):
    return {
        "arg_name": arg.arg_name,
        "is_keyword_arg": arg.is_keyword_arg,
        "is_star_arg": arg.is_star_arg,
        "arg_type": arg.arg_type,
        "default_value": arg.default_value,
    }


def keyword_to_dict(keyword):
    from robotframework_ls.impl.robot_specbuilder import docs_and_format

    keyword = keyword
    return {
        "name": keyword.name,
        "args": [arg_to_dict(arg) for arg in keyword.args],
        "doc": keyword.doc,
        "lineno": keyword.lineno,
        "tags": keyword.tags,
        "docs_and_format": docs_and_format(keyword),
    }


def test_libspec(libspec_manager, workspace_dir, data_regression):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc
    from typing import List

    os.makedirs(workspace_dir)
    libspec_manager.add_additional_pythonpath_folder(workspace_dir)
    path = Path(workspace_dir) / "check_lib.py"
    path.write_text(
        """
def method(a:int=10):
    '''
    :param a: This is the parameter a.
    '''

def method2(a:int):
    pass

def method3(a=10):
    pass
    
def method4(a=10, *args, **kwargs):
    pass
    
def method5(a, *args, **kwargs):
    pass
    
def method6():
    pass
"""
    )

    library_info: Optional[LibraryDoc] = libspec_manager.get_library_info("check_lib")
    assert library_info is not None
    keywords: List[KeywordDoc] = library_info.keywords
    data_regression.check([keyword_to_dict(k) for k in keywords])
    assert (
        int(library_info.specversion) <= 3
    ), "Libpsec version changed. Check parsing. "


def test_libspec_cache_no_lib(libspec_manager, workspace_dir):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    import time
    from robocorp_ls_core.basic import wait_for_condition

    os.makedirs(workspace_dir)
    libspec_manager.add_additional_pythonpath_folder(workspace_dir)

    def disallow_cached_create_libspec(*args, **kwargs):
        raise AssertionError("Should not be called")

    library_info: Optional[LibraryDoc] = libspec_manager.get_library_info("check_lib")
    assert library_info is None

    # Make sure that we don't try to create it anymore for the same lib.
    original_cached_create_libspec = libspec_manager._cached_create_libspec
    libspec_manager._cached_create_libspec = disallow_cached_create_libspec
    library_info: Optional[LibraryDoc] = libspec_manager.get_library_info("check_lib")
    assert library_info is None
    libspec_manager._cached_create_libspec = original_cached_create_libspec

    time.sleep(0.1)

    path = Path(workspace_dir) / "check_lib.py"
    path.write_text(
        """
def method2(a:int):
    pass
"""
    )
    # Check that the cache invalidation is in place!
    wait_for_condition(
        lambda: libspec_manager.get_library_info("check_lib") is not None,
        msg="Did not recreate library in the available timeout.",
    )


def test_libspec_no_rest(libspec_manager, workspace_dir):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc

    os.makedirs(workspace_dir)
    libspec_manager.add_additional_pythonpath_folder(workspace_dir)

    path = Path(workspace_dir) / "check_lib.py"
    path.write_text(
        r'''
"""Example library in reStructuredText format.

- Formatting with **bold** and *italic*.
- URLs like http://example.com are turned to links.
- Custom links like reStructuredText__ are supported.
- Linking to \`My Keyword\` works but requires backtics to be escaped.

__ http://docutils.sourceforge.net

.. code:: robotframework

    *** Test Cases ***
    Example
        My keyword    # How cool is this!!?!!?!1!!
"""
ROBOT_LIBRARY_DOC_FORMAT = 'reST'

def my_keyword():
    """Nothing more to see here."""
'''
    )

    try:
        import docutils  # noqa
    except ImportError:
        pass
    else:
        original = libspec_manager._subprocess_check_output
        # If docutils is installed, mock it (otherwise, just execute as usual).

        def raise_error(cmdline, *args, **kwargs):
            from subprocess import CalledProcessError

            if "--docformat" not in cmdline:
                raise CalledProcessError(
                    1,
                    cmdline,
                    b"reST format requires 'docutils' module to be installed",
                    b"",
                )
            return original(cmdline, *args, **kwargs)

        libspec_manager._subprocess_check_output = raise_error

    library_info: Optional[LibraryDoc] = libspec_manager.get_library_info("check_lib")
    assert library_info is not None


def test_libspec_manager_caches(libspec_manager, workspace_dir):
    from robocorp_ls_core import uris
    import os.path
    from robotframework_ls_tests.fixtures import LIBSPEC_1
    from robotframework_ls_tests.fixtures import LIBSPEC_2
    from robotframework_ls_tests.fixtures import LIBSPEC_2_A
    import time
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition

    workspace_dir_a = os.path.join(workspace_dir, "workspace_dir_a")
    os.makedirs(workspace_dir_a)
    with open(os.path.join(workspace_dir_a, "my.libspec"), "w") as stream:
        stream.write(LIBSPEC_1)
    libspec_manager.add_workspace_folder(uris.from_fs_path(workspace_dir_a))
    assert libspec_manager.get_library_info("case1_library", create=False) is not None

    libspec_manager.remove_workspace_folder(uris.from_fs_path(workspace_dir_a))
    library_info = libspec_manager.get_library_info("case1_library", create=False)
    if library_info is not None:
        raise AssertionError(
            "Expected: %s to be None after removing %s"
            % (library_info, uris.from_fs_path(workspace_dir_a))
        )

    libspec_manager.add_workspace_folder(uris.from_fs_path(workspace_dir_a))
    assert libspec_manager.get_library_info("case1_library", create=False) is not None

    # Give a timeout so that the next write will have at least 1 second
    # difference (1s is the minimum for poll to work).
    time.sleep(1.1)
    with open(os.path.join(workspace_dir_a, "my2.libspec"), "w") as stream:
        stream.write(LIBSPEC_2)

    def check_spec_found():
        library_info = libspec_manager.get_library_info("case2_library", create=False)
        return library_info is not None

    # Updating is done in a thread.
    wait_for_test_condition(check_spec_found, sleep=1 / 5.0)

    library_info = libspec_manager.get_library_info("case2_library", create=False)
    assert set(x.name for x in library_info.keywords) == set(
        ["Case 2 Verify Another Model", "Case 2 Verify Model"]
    )

    # Give a timeout so that the next write will have at least 1 second
    # difference (1s is the minimum for poll to work).
    time.sleep(1)
    with open(os.path.join(workspace_dir_a, "my2.libspec"), "w") as stream:
        stream.write(LIBSPEC_2_A)

    def check_spec_2_a():
        library_info = libspec_manager.get_library_info("case2_library", create=False)
        if library_info:
            return set(x.name for x in library_info.keywords) == set(
                ["Case 2 A Verify Another Model", "Case 2 A Verify Model"]
            )

    # Updating is done in a thread.
    wait_for_test_condition(check_spec_2_a, sleep=1 / 5.0)
