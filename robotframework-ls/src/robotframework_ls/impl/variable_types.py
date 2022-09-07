from typing import Optional, Tuple, Any

from robocorp_ls_core.cache import instance_cache
from robocorp_ls_core.protocols import check_implements
from robotframework_ls.impl.protocols import (
    VariableKind,
    IVariableFound,
    ICompletionContext,
    INode,
    LOCAL_ASSIGNS_VARIABLE_KIND,
)


class VariableFoundFromToken(object):
    def __init__(
        self,
        completion_context,
        variable_token,
        variable_value,
        variable_name=None,
        variable_kind=VariableKind.VARIABLE,
        stack: Tuple[INode, ...] = None,
    ):
        self.completion_context = completion_context
        self.stack = stack
        self.variable_token = variable_token

        if variable_name is None:
            variable_name = variable_token.value

        self.variable_name = variable_name
        if isinstance(variable_value, (list, tuple, set)):
            if len(variable_value) == 1:
                self.variable_value = str(next(iter(variable_value)))
            else:
                self.variable_value = str(variable_value)
        else:
            self.variable_value = str(variable_value)
        self.variable_kind = variable_kind
        self._is_local_variable = self.variable_kind in LOCAL_ASSIGNS_VARIABLE_KIND
        if self._is_local_variable:
            assert (
                stack
            ), f"Stack not available for local variable: {self.variable_name} at line: {self.lineno}"

    @property
    def is_local_variable(self):
        return self._is_local_variable

    @property  # type: ignore
    @instance_cache
    def source(self):
        from robocorp_ls_core import uris

        return uris.to_fs_path(self.completion_context.doc.uri)

    @property
    def lineno(self):
        return self.variable_token.lineno - 1  # Make 0-based

    @property
    def end_lineno(self):
        return self.variable_token.lineno - 1  # Make 0-based

    @property
    def col_offset(self):
        return self.variable_token.col_offset

    @property
    def end_col_offset(self):
        return self.variable_token.end_col_offset

    def __typecheckself__(self) -> None:
        _: IVariableFound = check_implements(self)

    def __str__(self):
        return f"{self.__class__.__name__}({self.variable_name})"

    __repr__ = __str__


class VariableFoundFromPythonAst(object):
    def __init__(
        self,
        path: str,
        lineno: int,
        col: int,
        end_lineno: int,
        end_col: int,
        variable_value: str,
        variable_name: str,
    ):
        self.lineno = lineno
        self.col_offset = col
        self.end_lineno = end_lineno
        self.end_col_offset = end_col

        self.completion_context: Optional[ICompletionContext] = None
        self._path = path
        self.variable_name = variable_name
        self.variable_value = variable_value
        self.variable_kind = VariableKind.PYTHON
        self.stack: Optional[Tuple[INode, ...]] = None

    @property
    def is_local_variable(self):
        return False

    @property
    def source(self):
        return self._path

    def __typecheckself__(self) -> None:
        _: IVariableFound = check_implements(self)

    def __str__(self):
        return f"{self.__class__.__name__}({self.variable_name})"

    __repr__ = __str__


class VariableFoundFromSettings(object):
    variable_kind: str = VariableKind.SETTINGS

    def __init__(
        self, variable_name: str, variable_value: Any, source: str = "", lineno: int = 0
    ):
        self.completion_context: Optional[ICompletionContext] = None
        self.variable_name: str = variable_name
        self.variable_value: str = str(variable_value)
        self._source: str = source
        self._lineno: int = lineno
        self.stack: Optional[Tuple[INode, ...]] = None

    @property
    def is_local_variable(self):
        return False

    @property
    def source(self):
        return self._source

    @property
    def lineno(self):
        return self._lineno

    @property
    def end_lineno(self):
        return self._lineno

    @property
    def col_offset(self):
        return 0

    @property
    def end_col_offset(self):
        return 0

    def __typecheckself__(self) -> None:
        _: IVariableFound = check_implements(self)

    def __str__(self):
        return f"{self.__class__.__name__}({self.variable_name})"

    __repr__ = __str__


class VariableFoundFromBuiltins(VariableFoundFromSettings):
    variable_kind = VariableKind.BUILTIN


class VariableFoundFromYaml(VariableFoundFromSettings):
    variable_kind = VariableKind.YAML


class VariableFoundFromArgumentsFile(VariableFoundFromSettings):
    variable_kind = VariableKind.ARGUMENTS_FILE
