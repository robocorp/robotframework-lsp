from robotframework_ls.impl.robot_version import get_robot_major_version
import pytest
import os
from typing import List
from pathlib import Path
from robocorp_ls_core.protocols import IDocument
from contextlib import contextmanager


def embed_errors_into_file(ws, doc, config=None) -> IDocument:
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_analysis import collect_analysis_errors
    from robocorp_ls_core.workspace import Document
    from robocorp_ls_core.lsp import RangeTypedDict
    from robocorp_ls_core.lsp import TextEdit
    from robocorp_ls_core.lsp import TextDocumentItem

    contents_without_added_docs = []
    delimiter = None
    for line in doc.iter_lines(keep_ends=True):
        if line.startswith("#!"):
            continue
        if delimiter is None:
            if line.endswith("\r\n"):
                delimiter = "\r\n"
            elif line.endswith("\r"):
                delimiter = "\r"
        contents_without_added_docs.append(line)
    if delimiter is None:
        delimiter = "\n"

    doc = ws.put_document(
        TextDocumentItem(doc.uri, text="".join(contents_without_added_docs))
    )
    completion_context = CompletionContext(doc, workspace=ws, config=config)

    errors = [
        error.to_lsp_diagnostic()
        for error in collect_analysis_errors(completion_context)
    ]

    def key(diagnostic):
        return (
            diagnostic["range"]["start"]["line"],
            diagnostic["range"]["start"]["character"],
            diagnostic["message"],
        )

    new_doc = Document("<no-uri>", "".join(contents_without_added_docs))
    errors = sorted(errors, key=key)
    changes: List[TextEdit] = []
    for error in errors:
        line = error["range"]["start"]["line"] + 1
        character = error["range"]["start"]["character"]

        endline = error["range"]["end"]["line"] + 1
        endcharacter = error["range"]["end"]["character"]
        start = "#!" + (" " * (character - 2))
        if line == endline:
            cols = endcharacter - character
            prefix = start + ("^" * cols) + " "
        else:
            prefix = start + "^-> <next line> "

        msg = error["message"]
        lines = [x for x in msg.splitlines() if x.strip()]
        text = ""
        for l in lines:
            text += prefix + l + delimiter

        r: RangeTypedDict = {
            "start": {"line": line, "character": 0},
            "end": {"line": line, "character": 0},
        }
        changes.append(TextEdit(r, text))
    new_doc.apply_text_edits(changes)

    return new_doc


def test_embed_info_into_file(workspace, libspec_manager):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Undefined arg
    Log to Console    ${a}+${bbbb}
"""
    new_doc = embed_errors_into_file(workspace.ws, doc)
    assert (
        new_doc.source
        == """
*** Keywords ***
Undefined arg
    Log to Console    ${a}+${bbbb}
#!                      ^ Undefined variable: a
#!                           ^^^^ Undefined variable: bbbb
"""
    )

    # Reapplying should give the same output.
    doc = workspace.put_doc("case2.robot", new_doc.source)
    new_doc2 = embed_errors_into_file(workspace.ws, doc)
    assert new_doc.source == new_doc2.source


_RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "_resources")
_CASE_ROOT_KEYWORDS = os.path.join(_RESOURCES_DIR, "atest_v5", "keywords")
_CASE_ROOT_VARIABLES = os.path.join(_RESOURCES_DIR, "atest_v5", "variables")


@contextmanager
def _make_ws(tmpdir, caseroot, pythonpath):
    from robocorp_ls_core.watchdog_wrapper import create_observer
    from robotframework_ls.impl.libspec_manager import LibspecManager
    from robotframework_ls.impl import workspace_symbols as workspace_symbols_module
    from robotframework_ls.robot_config import RobotConfig
    from robocorp_ls_core import uris
    from robotframework_ls.impl.robot_workspace import RobotWorkspace
    from robocorp_ls_core.lsp import WorkspaceFolder

    workspace_symbols_module.WORKSPACE_SYMBOLS_TIMEOUT = 5

    fs_observer = create_observer("dummy", ())

    libspec_manager = LibspecManager(
        user_libspec_dir=str(tmpdir.join("user_libspec")),
        cache_libspec_dir=str(tmpdir.join("cache_libspec")),
        observer=fs_observer,
        dir_cache_dir=str(tmpdir.join(".cache")),
    )

    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": pythonpath,
                "libraries": {"libdoc": {"needsArgs": ["*"]}},
            }
        }
    )
    libspec_manager.config = config

    workspace_folder = WorkspaceFolder(
        uris.from_fs_path(caseroot), os.path.basename(caseroot)
    )
    ws = RobotWorkspace(
        uris.from_fs_path(caseroot),
        fs_observer=fs_observer,
        libspec_manager=libspec_manager,
        workspace_folders=[workspace_folder],
    )

    try:
        yield ws
    finally:
        libspec_manager.dispose()
        ws.dispose()


@pytest.fixture(scope="session")
def atest_keywords_ws(tmp_path_factory):

    from py.path import local

    tmpdir = local(tmp_path_factory.mktemp("atest_keywords_tmp"))
    with _make_ws(
        tmpdir,
        _CASE_ROOT_KEYWORDS,
        [
            _CASE_ROOT_KEYWORDS,
            os.path.join(_CASE_ROOT_KEYWORDS, "resources"),
        ],
    ) as ws:
        yield ws


@pytest.fixture(scope="session")
def atest_variables_ws(tmp_path_factory):

    from py.path import local

    tmpdir = local(tmp_path_factory.mktemp("atest_variables_tmp"))
    with _make_ws(
        tmpdir,
        _CASE_ROOT_VARIABLES,
        [
            _CASE_ROOT_VARIABLES,
        ],
    ) as ws:
        yield ws


def _ACCEPT_PATH(p):
    # return p.name == "embedded_arguments_library_keywords.robot"
    return True


def _list_paths_in_folder(caseroot):
    paths = []
    for p in Path(caseroot).rglob("*"):
        if not _ACCEPT_PATH(p):
            if "GITHUB_ACTIONS" in os.environ:
                raise AssertionError(
                    "_ACCEPT_PATH should accept all in Github actions."
                )
            continue

        if p.name.endswith((".robot", ".resource")):
            if p.name == "common_resource.robot":
                continue

            # if p.name != "dots_in_keyword_name.robot":
            #     continue

            paths.append(p)
    return paths


# Note: we set it using parametrize so that we can run tests in parallel for
# each file instead of just sequentially.
_paths_keywords: List[Path] = []
_paths_variables: List[Path] = []
if get_robot_major_version() == 5:
    _paths_keywords = _list_paths_in_folder(_CASE_ROOT_KEYWORDS)
    _paths_variables = _list_paths_in_folder(_CASE_ROOT_VARIABLES)


def _check_path(ws, p, request):
    from robocorp_ls_core import uris

    config = ws.libspec_manager.config
    uri = uris.from_fs_path(str(p))
    doc = ws.get_document(uri, accept_from_file=True)
    new_doc = embed_errors_into_file(ws, doc, config)
    if doc.source != new_doc.source:
        if request.config.getoption("force_regen"):
            p.write_text(new_doc.source, encoding="utf-8")

        obtained_lines = new_doc.source.splitlines()
        expected_lines = doc.source.splitlines()

        if obtained_lines != expected_lines:
            import difflib

            diff_lines = list(
                difflib.unified_diff(expected_lines, obtained_lines, lineterm="")
            )

            diff = ["FILES DIFFER"]
            diff += diff_lines
            raise AssertionError("\n".join(diff))


@pytest.mark.skipif(get_robot_major_version() != 5, reason="RF-5 only test")
@pytest.mark.parametrize(
    "p",
    _paths_keywords,
    ids=[x.name for x in _paths_keywords],
)
def test_atest_keywords(atest_keywords_ws, p, request):
    _check_path(atest_keywords_ws, p, request)


@pytest.mark.skipif(get_robot_major_version() != 5, reason="RF-5 only test")
@pytest.mark.parametrize("p", _paths_variables, ids=[x.name for x in _paths_variables])
def test_atest_variables(atest_variables_ws, p, request):
    _check_path(atest_variables_ws, p, request)
