from typing import Optional, Tuple
import os
from robotframework_ls.impl.protocols import IVariableFound
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class VariablesFromVariablesFileLoader:
    def __init__(self, path: str):
        self._path = path
        self._mtime: Optional[float] = None
        self._variables: Tuple[IVariableFound, ...] = ()

    def __str__(self):
        return f"[VariablesFromVariablesFileLoader({self._path})]"

    __repr__ = __str__

    def _iter_vars(self, content):
        start_multiline = ["(", "[", "{"]
        end_multiline = [")", "]", "}"]
        multiline = ""
        multiple_lines = 0
        for lineno, line in enumerate(content.splitlines()):
            line = line.strip()

            if line.startswith("#"):
                continue

            if "#" in line:
                line = line.split("#", 1)[0]

            if any(special_character in line for special_character in start_multiline):
                multiple_lines += 1

            if multiple_lines != 0:
                multiline += line

            if any(special_character in line for special_character in end_multiline):
                multiple_lines -= 1
                if multiple_lines == 0:
                    line = multiline

            if line and multiple_lines == 0:
                yield line, lineno

    def get_variables(self) -> Tuple[IVariableFound, ...]:
        from robotframework_ls.impl.variable_types import VariableFoundFromVariablesFile

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
                for var, lineno in self._iter_vars(content):
                    if "=" not in var:
                        log.info(
                            '"=" not found in: %s when reading variables from: %s',
                            var,
                            path,
                        )
                        continue

                    variable_name, variable_value = var.split("=", 1)
                    variables.append(
                        VariableFoundFromVariablesFile(
                            variable_name, variable_value, path, lineno
                        )
                    )

                log.debug("Found variables from %s: %s", path, variables)
                self._variables = tuple(variables)
        except:
            log.exception(f"Error getting variables from {path}")

        return self._variables
