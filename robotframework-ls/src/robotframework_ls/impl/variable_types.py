from typing import Optional

from robocorp_ls_core.cache import instance_cache
from robocorp_ls_core.protocols import check_implements
from robotframework_ls.impl.protocols import (
    VariableKind,
    IVariableFound,
    ICompletionContext,
)


class VariableFoundFromToken(object):
    def __init__(
        self,
        completion_context,
        variable_token,
        variable_value,
        variable_name=None,
        variable_kind=VariableKind.VARIABLE,
    ):
        self.completion_context = completion_context
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

    @property
    def source(self):
        return self._path

    def __typecheckself__(self) -> None:
        _: IVariableFound = check_implements(self)

    def __str__(self):
        return f"{self.__class__.__name__}({self.variable_name})"

    __repr__ = __str__


class VariableFoundFromSettings(object):
    variable_kind = VariableKind.SETTINGS

    def __init__(self, variable_name, variable_value, source="", lineno=0):
        self.completion_context = None
        self.variable_name = variable_name
        self.variable_value = str(variable_value)
        self._source = source
        self._lineno = lineno

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
