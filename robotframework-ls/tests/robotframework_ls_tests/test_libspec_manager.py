import os
from pathlib import Path
from typing import Optional
from robocorp_ls_core import uris


def test_libspec_info(libspec_manager, tmpdir):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    assert "BuiltIn" in libspec_manager.get_library_names()
    uri = uris.from_fs_path(str(tmpdir.join("case.robot")))
    lib_info = libspec_manager.get_library_doc_or_error(
        "BuiltIn",
        create=False,
        completion_context=CompletionContext(RobotDocument(uri, "")),
    ).library_doc
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


def test_libspec(libspec_manager, workspace_dir, data_regression) -> None:
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc
    from typing import List
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

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

    uri = uris.from_fs_path(os.path.join(workspace_dir, "case.robot"))
    library_info: Optional[LibraryDoc] = libspec_manager.get_library_doc_or_error(
        "check_lib", True, CompletionContext(RobotDocument(uri, ""))
    ).library_doc
    assert library_info is not None
    keywords: List[KeywordDoc] = library_info.keywords
    data_regression.check([keyword_to_dict(k) for k in keywords])
    assert (
        int(library_info.specversion) <= 6
    ), "Libspec version changed. Check parsing. "


def test_libspec_string_source(libspec_manager, workspace_dir, data_regression):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc
    from typing import List
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    os.makedirs(workspace_dir)
    libspec_manager.add_additional_pythonpath_folder(workspace_dir)
    path = Path(workspace_dir) / "check_lib.py"
    path.write_text(
        """
exec('''
def method():
    pass
''')
"""
    )

    uri = uris.from_fs_path(os.path.join(workspace_dir, "case.robot"))
    library_info: Optional[LibraryDoc] = libspec_manager.get_library_doc_or_error(
        "check_lib", True, CompletionContext(RobotDocument(uri, ""))
    ).library_doc
    assert library_info is not None
    keywords: List[KeywordDoc] = library_info.keywords
    data_regression.check([keyword_to_dict(k) for k in keywords])


def test_libspec_rest(libspec_manager, workspace_dir, data_regression):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc
    from typing import List
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.completion_context import CompletionContext

    os.makedirs(workspace_dir)
    libspec_manager.add_additional_pythonpath_folder(workspace_dir)
    path = Path(workspace_dir) / "CheckLib.py"
    path.write_text(
        '''
from robot.api.deco import library, keyword

@library(scope="GLOBAL", doc_format="REST", auto_keywords=False)
class CheckLib:
    @keyword("My method")
    def my_method(self) -> None:
        """Do something with rest.
        
        .. code-block:: robotframework

            FOR    ${a}   IN    @{b}
                Do Something
            END
        """
'''
    )

    uri = uris.from_fs_path(os.path.join(workspace_dir, "case.robot"))
    library_info: Optional[LibraryDoc] = libspec_manager.get_library_doc_or_error(
        "CheckLib", True, CompletionContext(RobotDocument(uri, ""))
    ).library_doc

    assert library_info is not None
    assert library_info.doc_format == "REST"
    keywords: List[KeywordDoc] = library_info.keywords
    data_regression.check([keyword_to_dict(k) for k in keywords])


def test_libspec_cache_no_lib(libspec_manager, workspace_dir):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    import time
    from robocorp_ls_core.basic import wait_for_condition
    import sys
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    os.makedirs(workspace_dir)
    libspec_manager.add_additional_pythonpath_folder(workspace_dir)

    def disallow_cached_create_libspec(*args, **kwargs):
        raise AssertionError("Should not be called")

    uri = uris.from_fs_path(os.path.join(workspace_dir, "case.robot"))
    library_info: Optional[LibraryDoc] = libspec_manager.get_library_doc_or_error(
        "check_lib", True, CompletionContext(RobotDocument(uri, ""))
    ).library_doc
    assert library_info is None

    # Make sure that we don't try to create it anymore for the same lib.
    original_cached_create_libspec = libspec_manager._cached_create_libspec
    libspec_manager._cached_create_libspec = disallow_cached_create_libspec
    library_info: Optional[LibraryDoc] = libspec_manager.get_library_doc_or_error(
        "check_lib", True, CompletionContext(RobotDocument(uri, ""))
    ).library_doc
    assert library_info is None
    libspec_manager._cached_create_libspec = original_cached_create_libspec

    # The difference is on the default filesystem native vs polling approach.
    if sys.platform == "win32":
        time.sleep(0.2)
    else:
        time.sleep(3)

    path = Path(workspace_dir) / "check_lib.py"
    path.write_text(
        """
def method2(a:int):
    pass
"""
    )
    # Check that the cache invalidation is in place!
    wait_for_condition(
        lambda: libspec_manager.get_library_doc_or_error(
            "check_lib", True, CompletionContext(RobotDocument(uri, ""))
        ).library_doc
        is not None,
        msg="Did not recreate library in the available timeout.",
        timeout=15,
    )


def test_libspec_no_rest(libspec_manager, workspace_dir):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.completion_context import CompletionContext

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

    uri = uris.from_fs_path(os.path.join(workspace_dir, "case.robot"))
    library_info: Optional[LibraryDoc] = libspec_manager.get_library_doc_or_error(
        "check_lib", True, CompletionContext(RobotDocument(uri, ""))
    ).library_doc
    assert library_info is not None


def test_libspec_manager_caches(libspec_manager, workspace_dir):
    import os.path
    from robotframework_ls_tests.fixtures import LIBSPEC_1
    from robotframework_ls_tests.fixtures import LIBSPEC_2
    from robotframework_ls_tests.fixtures import LIBSPEC_2_A
    import time
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    workspace_dir_a = os.path.join(workspace_dir, "workspace_dir_a")
    os.makedirs(workspace_dir_a)
    with open(os.path.join(workspace_dir_a, "my.libspec"), "w") as stream:
        stream.write(LIBSPEC_1)
    libspec_manager.add_workspace_folder(uris.from_fs_path(workspace_dir_a))
    uri = uris.from_fs_path(os.path.join(workspace_dir, "case.robot"))
    assert (
        libspec_manager.get_library_doc_or_error(
            "case1_library",
            create=False,
            completion_context=CompletionContext(RobotDocument(uri, "")),
        ).library_doc
        is not None
    )

    libspec_manager.remove_workspace_folder(uris.from_fs_path(workspace_dir_a))
    library_info = libspec_manager.get_library_doc_or_error(
        "case1_library", False, CompletionContext(RobotDocument(uri, ""))
    ).library_doc
    if library_info is not None:
        raise AssertionError(
            "Expected: %s to be None after removing %s"
            % (library_info, uris.from_fs_path(workspace_dir_a))
        )

    libspec_manager.add_workspace_folder(uris.from_fs_path(workspace_dir_a))
    assert (
        libspec_manager.get_library_doc_or_error(
            "case1_library", False, CompletionContext(RobotDocument(uri, ""))
        ).library_doc
        is not None
    )

    # Give a timeout so that the next write will have at least 1 second
    # difference (1s is the minimum for poll to work).
    time.sleep(1.1)
    with open(os.path.join(workspace_dir_a, "my2.libspec"), "w") as stream:
        stream.write(LIBSPEC_2)

    def check_spec_found():
        library_info = libspec_manager.get_library_doc_or_error(
            "case2_library", False, CompletionContext(RobotDocument(uri, ""))
        ).library_doc
        return library_info is not None

    # Updating is done in a thread.
    wait_for_test_condition(check_spec_found, sleep=1 / 5.0)

    library_info = libspec_manager.get_library_doc_or_error(
        "case2_library", False, CompletionContext(RobotDocument(uri, ""))
    ).library_doc
    assert set(x.name for x in library_info.keywords) == set(
        ["Case 2 Verify Another Model", "Case 2 Verify Model"]
    )

    # Give a timeout so that the next write will have at least 1 second
    # difference (1s is the minimum for poll to work).
    time.sleep(1)
    with open(os.path.join(workspace_dir_a, "my2.libspec"), "w") as stream:
        stream.write(LIBSPEC_2_A)

    def check_spec_2_a():
        library_info = libspec_manager.get_library_doc_or_error(
            "case2_library", False, CompletionContext(RobotDocument(uri, ""))
        ).library_doc
        if library_info:
            return set(x.name for x in library_info.keywords) == set(
                ["Case 2 A Verify Another Model", "Case 2 A Verify Model"]
            )

    # Updating is done in a thread.
    wait_for_test_condition(check_spec_2_a, sleep=1 / 5.0)


def test_libspec_manager_json_html(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    import json

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    completion_context = CompletionContext(doc)

    library_doc = libspec_manager.get_library_doc_or_error(
        "case1_library",
        create=True,
        completion_context=completion_context,
    ).library_doc
    assert library_doc.doc_format == "ROBOT"
    library_doc.convert_docs_to_markdown()
    assert library_doc.doc_format == "markdown"
    as_json = json.dumps(library_doc.to_dictionary())
    assert "<p>" not in as_json

    # While the default is ROBOT and converts to markdown on request, when we
    # select the html_json format it always pre-converts internally before and
    # always provides as html without any additional work (this is done because
    # the conversion may be a slow process, but for the html_json we need to
    # have it fully converted before using anyways whereas in the default usage
    # we may just use it partially, so, we schedule the conversion in a thread
    # and use convert as needed in the regular case).

    libspec_manager = libspec_manager.create_copy()
    library_doc = libspec_manager.get_library_doc_or_error(
        "case1_library",
        create=True,
        completion_context=completion_context,
    ).library_doc
    assert library_doc.doc_format == "ROBOT"
    library_doc.convert_docs_to_html()
    assert library_doc.doc_format == "HTML"

    as_json = json.dumps(library_doc.to_dictionary())
    assert "<p>" in as_json


def test_libspec_manager_json_html_builtin(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    completion_context = CompletionContext(doc)

    libspec_manager = libspec_manager.create_copy()
    library_doc = libspec_manager.get_library_doc_or_error(
        "Collections",
        create=True,
        completion_context=completion_context,
    ).library_doc
    assert library_doc.doc_format == "HTML"
    import json

    as_json = json.dumps(library_doc.to_dictionary())
    assert '"name": "Collections"' in as_json
    assert "<p>" in as_json


def test_libspec_manager_basic(workspace, libspec_manager):
    from robotframework_ls.impl import robot_constants
    from robotframework_ls.impl.robot_version import get_robot_major_version

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")

    def get_library_doc_or_error(*args, **kwargs):
        from robotframework_ls.impl.completion_context import CompletionContext

        kwargs["completion_context"] = CompletionContext(doc)
        if "create" not in kwargs:
            kwargs["create"] = True
        return libspec_manager.get_library_doc_or_error(*args, **kwargs)

    assert get_library_doc_or_error("case1_library").library_doc is not None
    libspec_file = os.path.join(
        libspec_manager.user_libspec_dir, "case1_library.libspec"
    )
    # i.e.: We now save it with a hash for relative files, so, it's something as:
    # os.path.join(libspec_manager.user_libspec_dir, "781b0814.libspec")
    assert not os.path.exists(libspec_file)
    dir_contents = [
        x
        for x in os.listdir(libspec_manager.user_libspec_dir)
        if x.endswith(".libspec")
    ]
    assert len(dir_contents) == 1
    libspec_manager.synchronize_internal_libspec_folders()
    assert set(libspec_manager.get_library_names()).issuperset(
        ["case1_library"] + list(robot_constants.STDLIBS)
    )

    libdoc_or_error = get_library_doc_or_error("invalid")
    assert libdoc_or_error.library_doc is None
    if get_robot_major_version() >= 4:
        assert "Importing library 'invalid' failed" in libdoc_or_error.error
    else:
        assert "Importing test library 'invalid' failed" in libdoc_or_error.error

    # 2nd call should get error from cache
    libdoc_or_error = get_library_doc_or_error("invalid")
    assert libdoc_or_error.library_doc is None
    assert libdoc_or_error.library_doc is None
    if get_robot_major_version() >= 4:
        assert "Importing library 'invalid' failed" in libdoc_or_error.error
    else:
        assert "Importing test library 'invalid' failed" in libdoc_or_error.error

    library = get_library_doc_or_error("case1_library").library_doc

    assert tuple(kw.name for kw in library.keywords) == (
        "Check With Multi Args",
        "Verify Another Model",
        "Verify Model",
    )

    for d in dir_contents:
        os.remove(os.path.join(libspec_manager.user_libspec_dir, d))
    libspec_manager.synchronize_internal_libspec_folders()
    assert set(libspec_manager.get_library_names()).issuperset(robot_constants.STDLIBS)

    assert get_library_doc_or_error("case1_library", create=False).library_doc is None
    assert get_library_doc_or_error("case1_library").library_doc is not None
