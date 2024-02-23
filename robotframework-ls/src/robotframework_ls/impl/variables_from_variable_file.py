from typing import Optional, Tuple
import os
from robotframework_ls.impl.protocols import (
    IVariableFound,
    AbstractVariablesCollector,
    IRobotDocument,
)

from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class VariablesFromVariablesFileLoader:
    def __init__(self, path, robot_document: IRobotDocument) -> None:
        self._path = path
        self._robot_document = robot_document
        self._mtime: Optional[float] = None
        self._variables: Tuple[IVariableFound, ...] = ()

    def __str__(self):
        return f"[VariablesFromVariablesFileLoader({self._path, self._robot_document})]"

    __repr__ = __str__

    def get_variables(self) -> Tuple[IVariableFound, ...]:
        path = self._path
        robot_document = self._robot_document
        try:
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                log.info(
                    f"Unable to load variables from non-existent variables file: {path}."
                )
                return ()
            if mtime != self._mtime:
                log.debug("Loading variables from: %s", path)
                self._mtime = mtime
                python_ast = robot_document.get_python_ast()

                collector = _VariablesCollector()

                from robotframework_ls.impl.variable_completions_from_py import (
                    collect_variables_from_python_ast,
                )

                collect_variables_from_python_ast(python_ast, robot_document, collector)

                variables = collector.get_variables()

                log.debug("Found variables from %s: %s", path, variables)
                self._variables = tuple(variables)
        except Exception:
            log.exception(f"Error getting variables from {path}")

        return self._variables


class _VariablesCollector(AbstractVariablesCollector):
    def __init__(self):
        self.variables = []

    def accepts(self, variable_name: str) -> bool:
        return True

    def get_variables(self):
        return self.variables

    def on_variable(self, variable_found: IVariableFound):
        from robotframework_ls.impl.variable_types import VariableFoundFromVariablesFile

        self.variables.append(
            VariableFoundFromVariablesFile(
                variable_found.variable_name,
                variable_found.variable_value,
                variable_found.source,
                variable_found.lineno,
            )
        )
