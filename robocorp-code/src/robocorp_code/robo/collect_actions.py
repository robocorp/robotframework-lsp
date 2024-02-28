import ast as ast_module
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple, TypedDict

from robocorp_ls_core import uris
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


def collect_py_files(root_path: Path) -> Iterator[Path]:
    for item in root_path.iterdir():
        if item.is_dir():
            yield from collect_py_files(item)
        elif item.suffix == ".py":
            yield item


def _iter_nodes(
    node, internal_stack: Optional[List[Any]] = None, recursive=True
) -> Iterator[Tuple[List[Any], Any]]:
    """
    :note: the yielded stack is actually always the same (mutable) list, so,
    clients that want to return it somewhere else should create a copy.
    """
    stack: List[Any]
    if internal_stack is None:
        stack = []
        if node.__class__.__name__ != "File":
            stack.append(node)
    else:
        stack = internal_stack

    if recursive:
        for _field, value in ast_module.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast_module.AST):
                        yield stack, item
                        stack.append(item)
                        yield from _iter_nodes(item, stack, recursive=True)
                        stack.pop()

            elif isinstance(value, ast_module.AST):
                yield stack, value
                stack.append(value)

                yield from _iter_nodes(value, stack, recursive=True)

                stack.pop()
    else:
        # Not recursive
        for _field, value in ast_module.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast_module.AST):
                        yield stack, item

            elif isinstance(value, ast_module.AST):
                yield stack, value


def _collect_actions_from_file(p: Path) -> Iterator[ast_module.FunctionDef]:
    action_contents_file = p.read_bytes()
    ast = ast_module.parse(action_contents_file, "<string>")
    for _stack, node in _iter_nodes(ast, recursive=False):
        if isinstance(node, ast_module.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast_module.Call):
                    # Case for @action(is_consequential=True)
                    decorator = decorator.func

                # Case for @action
                if isinstance(decorator, ast_module.Name) and decorator.id == "action":
                    yield node


class PositionTypedDict(TypedDict):
    # Line position in a document (zero-based).
    line: int

    # Character offset on a line in a document (zero-based). Assuming that
    # the line is represented as a string, the `character` value represents
    # the gap between the `character` and `character + 1`.
    #
    # If the character value is greater than the line length it defaults back
    # to the line length.
    character: int


class RangeTypedDict(TypedDict):
    start: PositionTypedDict
    end: PositionTypedDict


class ActionInfoTypedDict(TypedDict):
    range: RangeTypedDict
    name: str
    uri: str


def _make_action_info(uri: str, node: ast_module.FunctionDef) -> ActionInfoTypedDict:
    coldelta = 4

    return {
        "range": {
            "start": {"line": node.lineno, "character": node.col_offset + coldelta},
            "end": {
                "line": node.lineno,
                "character": node.col_offset + coldelta + len(node.name),
            },
        },
        "name": node.name,
        "uri": uri,
    }


def iter_actions(root_directory: Path) -> Iterator[ActionInfoTypedDict]:
    f: Path
    for f in collect_py_files(root_directory):
        if "action" in f.name:
            try:
                for funcdef in _collect_actions_from_file(f):
                    yield _make_action_info(uris.from_fs_path(str(f)), funcdef)
            except Exception:
                log.error(f"Unable to collect @actions from {f}")
