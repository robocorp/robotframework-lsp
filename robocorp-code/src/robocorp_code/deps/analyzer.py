"""
This package should be independent of the rest as we can potentially make
it a standalone package in the future (maybe with a command line UI).
"""

import pathlib
from typing import Any, Iterator, Optional, Tuple, TypedDict, Union

import yaml


class _DiagnosticSeverity(object):
    Error = 1
    Warning = 2
    Information = 3
    Hint = 4


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


class _DiagnosticsTypedDict(TypedDict, total=False):
    # The range at which the message applies.
    range: RangeTypedDict

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

    def as_range(self) -> RangeTypedDict:
        assert self.location
        start_line, start_col, end_line, end_col = self.location
        return create_range_from_location(start_line, start_col, end_line, end_col)


def create_range_from_location(
    start_line: int,
    start_col: int,
    end_line: Optional[int] = None,
    end_col: Optional[int] = None,
) -> RangeTypedDict:
    """
    If the end_line and end_col aren't passed we consider
    that the location should go up until the end of the line.
    """
    if end_line is None:
        assert end_col is None
        end_line = start_line + 1
        end_col = 0
    assert end_col is not None
    dct: RangeTypedDict = {
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
        self.contents = contents
        self.path = path

    def iter_issues(self) -> Iterator[_DiagnosticsTypedDict]:
        from yaml.parser import ParserError

        from .conda_impl import conda_match_spec, conda_version

        diagnostic: _DiagnosticsTypedDict

        try:
            loader = LoaderWithLines(self.contents)
            path: pathlib.Path = pathlib.Path(self.path)

            loader.name = f".../{path.parent.name}/{path.name}"
            data = loader.get_single_data()
        except ParserError as e:
            diagnostic = {
                "range": create_range_from_location(
                    e.problem_mark.line, e.problem_mark.column
                ),
                "severity": _DiagnosticSeverity.Error,
                "source": "robocorp-code",
                "message": f"Syntax error: {e}",
            }
            yield diagnostic
            return

        dependencies = data.get(
            ScalarInfo(
                "dependencies",
                None,
            ),
        )

        # from pprint import pprint
        #
        # pprint(data)
        # pprint(dependencies)
        if dependencies:
            for dep in dependencies:
                # At this level we're seeing conda versions. The spec is:
                # https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
                # A bunch of code from conda was copied to handle that so that we
                # can just `conda_match_spec.parse_spec_str` to identify the version
                # we're dealing with.
                if isinstance(dep, ScalarInfo) and isinstance(dep.scalar, str):
                    try:
                        spec = conda_match_spec.parse_spec_str(dep.scalar)
                        version = spec["version"]
                        vspec = conda_version.VersionSpec(version)
                        name = spec["name"]
                    except Exception:
                        pass
                    else:
                        if name == "python":
                            # See: https://devguide.python.org/versions/
                            if not vspec.match("3.8"):  # 3.7 or earlier
                                diagnostic = {
                                    "range": dep.as_range(),
                                    "severity": _DiagnosticSeverity.Warning,
                                    "source": "robocorp-code",
                                    "message": f"The official support for versions lower than Python 3.8 has ended. "
                                    + " It is advisable to transition to a newer version "
                                    + "(Python 3.9 or newer is recommended).",
                                }

                                yield diagnostic
