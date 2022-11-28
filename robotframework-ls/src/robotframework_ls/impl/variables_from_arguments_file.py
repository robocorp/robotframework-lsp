from typing import Optional, Tuple
import os
from robotframework_ls.impl.protocols import IVariableFound
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class VariablesFromArgumentsFileLoader:
    def __init__(self, path: str):
        self._path = path
        self._mtime: Optional[float] = None
        self._variables: Tuple[IVariableFound, ...] = ()

    def __str__(self):
        return f"[VariablesFromArgumentsFileLoader({self._path})]"

    __repr__ = __str__

    def _iter_args(self, content):
        for lineno, line in enumerate(content.splitlines()):
            line = line.strip()

            if line.startswith("-"):
                for v in self._split_option(line):
                    yield v, lineno

            elif line and not line.startswith("#"):
                yield line, lineno

    def _split_option(self, line):
        separator = self._get_option_separator(line)
        if not separator:
            return [line]
        option, value = line.split(separator, 1)
        if separator == " ":
            value = value.strip()
        return [option, value]

    def _get_option_separator(self, line):
        if " " not in line and "=" not in line:
            return None
        if "=" not in line:
            return " "
        if " " not in line:
            return "="
        return " " if line.index(" ") < line.index("=") else "="

    def get_variables(self) -> Tuple[IVariableFound, ...]:
        from robotframework_ls.impl.variable_types import VariableFoundFromArgumentsFile

        path = self._path
        try:
            try:
                mtime = os.path.getmtime(path)
            except:
                log.info(
                    f"Unable to load variables from non-existent variables file: {path}."
                )
                return ()
            if mtime != self._mtime:
                log.debug("Loading variables from: %s", path)
                self._mtime = mtime
                with open(path, encoding="utf-8") as stream:
                    content = stream.read()

                if content.startswith("\ufeff"):
                    content = content[1:]

                variables = []
                last = None
                for arg, lineno in self._iter_args(content):
                    if last in ("-v", "--variable"):
                        if ":" not in arg:
                            log.info(
                                '":" not found in: %s when reading variables from: %s',
                                arg,
                                path,
                            )
                            continue

                        variable_name, variable_value = arg.split(":", 1)
                        variables.append(
                            VariableFoundFromArgumentsFile(
                                variable_name, variable_value, path, lineno
                            )
                        )
                    last = arg

                log.debug("Found variables from %s: %s", path, variables)
                self._variables = tuple(variables)
        except:
            log.exception(f"Error getting variables from {path}")

        return self._variables
