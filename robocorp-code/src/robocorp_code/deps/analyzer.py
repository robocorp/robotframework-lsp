"""
This package should be independent of the rest as we can potentially make
it a standalone package in the future (maybe with a command line UI).
"""

import pathlib
from typing import Any, Iterator, List, Optional, Tuple, TypedDict, Union

import yaml


class _DiagnosticSeverity(object):
    Error = 1
    Warning = 2
    Information = 3
    Hint = 4


class _PositionTypedDict(TypedDict):
    # Line position in a document (zero-based).
    line: int

    # Character offset on a line in a document (zero-based). Assuming that
    # the line is represented as a string, the `character` value represents
    # the gap between the `character` and `character + 1`.
    #
    # If the character value is greater than the line length it defaults back
    # to the line length.
    character: int


class _RangeTypedDict(TypedDict):
    start: _PositionTypedDict
    end: _PositionTypedDict


class _DiagnosticsTypedDict(TypedDict, total=False):
    # The range at which the message applies.
    range: _RangeTypedDict

    # The diagnostic's severity. Can be omitted. If omitted it is up to the
    # client to interpret diagnostics as error, warning, info or hint.
    severity: Optional[int]  # DiagnosticSeverity

    # The diagnostic's code, which might appear in the user interface.
    code: Union[int, str]

    # An optional property to describe the error code.
    #
    # @since 3.16.0
    codeDescription: Any

    # A human-readable string describing the source of this
    # diagnostic, e.g. 'typescript' or 'super lint'.
    source: Optional[str]

    # The diagnostic's message.
    message: str

    # Additional metadata about the diagnostic.
    #
    # @since 3.15.0
    tags: list  # DiagnosticTag[];

    # An array of related diagnostic information, e.g. when symbol-names within
    # a scope collide all definitions can be marked via this property.
    relatedInformation: list  # DiagnosticRelatedInformation[];

    # A data entry field that is preserved between a
    # `textDocument/publishDiagnostics` notification and
    # `textDocument/codeAction` request.
    #
    # @since 3.16.0
    data: Optional[Any]  # unknown;


class ScalarInfo:
    def __init__(self, scalar: Any, location: Optional[Tuple[int, int, int, int]]):
        """
        Args:
            scalar:
            location: tuple(start_line, start_col, end_line, end_col)
        """
        self.scalar = scalar
        self.location = location

    def __repr__(self):
        return repr(self.scalar)

    def __str__(self):
        return str(self.scalar)

    def __eq__(self, o):
        if isinstance(o, ScalarInfo):
            return self.scalar == o.scalar

        return False

    def __ne__(self, o):
        return not self == o

    def __hash__(self):
        return hash(self.scalar)

    def as_range(self) -> _RangeTypedDict:
        assert self.location
        start_line, start_col, end_line, end_col = self.location
        return create_range_from_location(start_line, start_col, end_line, end_col)


def create_range_from_location(
    start_line: int,
    start_col: int,
    end_line: Optional[int] = None,
    end_col: Optional[int] = None,
) -> _RangeTypedDict:
    """
    If the end_line and end_col aren't passed we consider
    that the location should go up until the end of the line.
    """
    if end_line is None:
        assert end_col is None
        end_line = start_line + 1
        end_col = 0
    assert end_col is not None
    dct: _RangeTypedDict = {
        "start": {
            "line": start_line,
            "character": start_col,
        },
        "end": {
            "line": end_line,
            "character": end_col,
        },
    }
    return dct


class LoaderWithLines(yaml.SafeLoader):
    def construct_scalar(self, node, *args, **kwargs):
        scalar = yaml.SafeLoader.construct_scalar(self, node, *args, **kwargs)
        return ScalarInfo(
            scalar=scalar,
            location=(
                node.start_mark.line,
                node.start_mark.column,
                node.end_mark.line,
                node.end_mark.column,
            ),
        )


class Analyzer:
    def __init__(self, contents: str, path: str):
        """
        Args:
            contents: The contents of the conda.yaml.
            path: The path for the conda yaml.
        """
        from ._conda_deps import CondaDeps
        from ._pip_deps import PipDeps
        from ._pypi_cloud import PyPiCloud

        self.contents = contents
        self.path = path

        self._loaded_conda_yaml = False
        self._load_errors: List[_DiagnosticsTypedDict] = []
        self._conda_data: Optional[dict] = None

        self._pip_deps = PipDeps()
        self._conda_deps = CondaDeps()
        self._pypi_cloud = PyPiCloud()

    def load_conda_yaml(self) -> None:
        if self._loaded_conda_yaml:
            return
        self._loaded_conda_yaml = True

        from yaml.parser import ParserError

        diagnostic: _DiagnosticsTypedDict

        try:
            loader = LoaderWithLines(self.contents)
            path: pathlib.Path = pathlib.Path(self.path)

            loader.name = f".../{path.parent.name}/{path.name}"
            data = loader.get_single_data()
            self._conda_data = data
        except ParserError as e:
            diagnostic = {
                "range": create_range_from_location(
                    e.problem_mark.line, e.problem_mark.column
                ),
                "severity": _DiagnosticSeverity.Error,
                "source": "robocorp-code",
                "message": f"Syntax error: {e}",
            }
            self._load_errors.append(diagnostic)
            return

        dependencies = data.get(
            ScalarInfo(
                "dependencies",
                None,
            ),
        )

        conda_versions = self._conda_deps
        pip_versions = self._pip_deps
        if dependencies:
            for dep in dependencies:
                # At this level we're seeing conda versions. The spec is:
                # https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
                # A bunch of code from conda was copied to handle that so that we
                # can just `conda_match_spec.parse_spec_str` to identify the version
                # we're dealing with.
                if isinstance(dep, ScalarInfo) and isinstance(dep.scalar, str):
                    conda_versions.add_dep(dep.scalar, dep.as_range())
                elif isinstance(dep, dict):
                    pip_deps = dep.get(ScalarInfo("pip", None))
                    if pip_deps:
                        for dep in pip_deps:
                            if isinstance(dep, ScalarInfo) and isinstance(
                                dep.scalar, str
                            ):
                                pip_versions.add_dep(dep.scalar, dep.as_range())

    def iter_issues(self) -> Iterator[_DiagnosticsTypedDict]:
        self.load_conda_yaml()
        if self._load_errors:
            yield from iter(self._load_errors)
            return

        data = self._conda_data
        if not data:
            return

        yield from self.iter_conda_issues()
        yield from self.iter_pip_issues()

    def iter_pip_issues(self):
        from robocorp_code.deps.pip_impl import pip_packaging_version

        for dep_info in self._pip_deps.iter_pip_dep_infos():
            if len(dep_info.constraints) == 1:
                # For now just checking versions '=='.
                constraint = next(iter(dep_info.constraints))
                if constraint[0] == "==":
                    local_version = constraint[1]
                    newer_cloud_versions = self._pypi_cloud.get_versions_newer_than(
                        dep_info.name, pip_packaging_version.parse(local_version)
                    )
                    if newer_cloud_versions:
                        latest_cloud_version = newer_cloud_versions[-1]
                        diagnostic = {
                            "range": dep_info.dep_range,
                            "severity": _DiagnosticSeverity.Warning,
                            "source": "robocorp-code",
                            "message": f"Consider updating '{dep_info.name}' to the latest version: '{latest_cloud_version}'. "
                            + f"Found {len(newer_cloud_versions)} versions newer than the current one: {', '.join(newer_cloud_versions)}.",
                        }

                        yield diagnostic

    def iter_conda_issues(self):
        diagnostic: _DiagnosticsTypedDict
        dep_vspec = self._conda_deps.get_dep_vspec("python")

        # See: https://devguide.python.org/versions/
        if dep_vspec is not None and not check_version(
            dep_vspec, ">3.8"
        ):  # 3.7 or earlier
            dep_range = self._conda_deps.get_dep_range("python")

            diagnostic = {
                "range": dep_range,
                "severity": _DiagnosticSeverity.Warning,
                "source": "robocorp-code",
                "message": "The official support for versions lower than Python 3.8 has ended. "
                + " It is advisable to transition to a newer version "
                + "(Python 3.9 or newer is recommended).",
            }

            yield diagnostic

        dep_vspec = self._conda_deps.get_dep_vspec("pip")

        if dep_vspec is not None and not check_version(
            dep_vspec, ">22"
        ):  # pip should be 22 or newer
            dep_range = self._conda_deps.get_dep_range("pip")

            diagnostic = {
                "range": dep_range,
                "severity": _DiagnosticSeverity.Warning,
                "source": "robocorp-code",
                "message": "Consider updating pip to a newer version (at least pip 22 onwards is recommended).",
            }

            yield diagnostic


def check_version(dep_vspec, constraint):
    op = dep_vspec.get_matcher(constraint)[1]
    return op(dep_vspec)
