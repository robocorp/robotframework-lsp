import os
import ast
from typing import List, Optional
import difflib

from robot.api.parsing import ModelVisitor, Token
from robot.parsing.model import Statement
from robot.utils.robotio import file_writer
from click import style


class StatementLinesCollector(ModelVisitor):
    """
    Used to get writeable presentation of Robot Framework model.
    """

    def __init__(self, model):
        self.text = ""
        self.visit(model)

    def visit_Statement(self, node):  # noqa
        for token in node.tokens:
            self.text += token.value

    def __eq__(self, other):
        return other.text == self.text


class GlobalFormattingConfig:
    def __init__(
        self,
        space_count: int,
        line_sep: str,
        start_line: Optional[int],
        end_line: Optional[int],
        separator: str,
    ):
        self.start_line = start_line
        self.end_line = end_line
        self.space_count = space_count

        if separator == "space":
            self.separator = " " * space_count
        elif separator == "tab":
            self.space_count = space_count
            self.separator = "\t"

        if line_sep == "windows":
            self.line_sep = "\r\n"
        elif line_sep == "unix":
            self.line_sep = "\n"
        elif line_sep == "auto":
            self.line_sep = "auto"
        else:
            self.line_sep = os.linesep


def decorate_diff_with_color(contents: List[str]) -> str:
    """Inject the ANSI color codes to the diff."""
    for i, line in enumerate(contents):
        if line.startswith("+++") or line.startswith("---"):
            line = style(line, bold=True, reset=True)
        elif line.startswith("@@"):
            line = style(line, fg="cyan", reset=True)
        elif line.startswith("+"):
            line = style(line, fg="green", reset=True)
        elif line.startswith("-"):
            line = style(line, fg="red", reset=True)
        contents[i] = line
    return "".join(contents)


def normalize_name(name):
    return name.lower().replace("_", "").replace(" ", "")


def after_last_dot(name):
    return name.split(".")[-1]


def node_within_lines(node_start, node_end, start_line, end_line):
    if start_line:
        if node_start < start_line:
            return False
        if end_line:
            if node_end > end_line:
                return False
        else:
            if start_line != node_start:
                return False
    return True


def node_outside_selection(node, formatting_config):
    """
    Contrary to ``node_within_lines`` it just checks if node is fully outside selected lines.
    Partial selection is useful for transformers like aligning code.
    """
    if (
        formatting_config.start_line
        and formatting_config.start_line > node.end_lineno
        or formatting_config.end_line
        and formatting_config.end_line < node.lineno
    ):
        return True
    return False


def split_args_from_name_or_path(name):
    """Split arguments embedded to name or path like ``Example:arg1:arg2``.

    The separator can be either colon ``:`` or semicolon ``;``. If both are used,
    the first one is considered to be the separator.
    """
    if os.path.exists(name):
        return name, []
    index = _get_arg_separator_index_from_name_or_path(name)
    if index == -1:
        return name, []
    args = _escaped_split(name[index + 1 :], name[index])
    name = name[:index]
    return name, args


def _escaped_split(string, delim):
    ret = []
    current = []
    itr = iter(string)
    for ch in itr:
        if ch == "\\":
            try:
                current.append("\\")
                current.append(next(itr))
            except StopIteration:
                pass
        elif ch == delim:
            ret.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        ret.append("".join(current))
    return ret


def _get_arg_separator_index_from_name_or_path(name):
    colon_index = name.find(":")
    # Handle absolute Windows paths
    if colon_index == 1 and name[2:3] in ("/", "\\"):
        colon_index = name.find(":", colon_index + 1)
    semicolon_index = name.find(";")
    if colon_index == -1:
        return semicolon_index
    if semicolon_index == -1:
        return colon_index
    return min(colon_index, semicolon_index)


def round_to_four(number):
    div = number % 4
    if div:
        return number + 4 - div
    return number


def any_non_sep(tokens):
    return any(token.type not in (Token.EOL, Token.SEPARATOR, Token.EOS) for token in tokens)


def tokens_by_lines(node):
    for line in node.lines:
        if not any_non_sep(line):
            continue
        if line:
            if line[0].type == Token.VARIABLE:
                if line[0].value:
                    line[0].value = line[0].value.lstrip()
                else:
                    # if variable is prefixed with spaces
                    line = line[1:]
            elif line[0].type == Token.ARGUMENT:
                line[0].value = line[0].value.strip() if line[0].value else line[0].value
        yield [token for token in line if token.type not in (Token.SEPARATOR, Token.EOS)]


def left_align(node):
    """remove leading separator token"""
    tokens = list(node.tokens)
    if tokens:
        tokens[0].value = tokens[0].value.lstrip(" \t")
    return Statement.from_tokens(tokens)


def remove_rst_formatting(text):
    return text.replace("::", ":").replace("``", "'")


class RecommendationFinder:
    def find_similar(self, name, candidates):
        norm_name = name.lower()
        norm_cand = self.get_normalized_candidates(candidates)
        matches = self.find(norm_name, norm_cand.keys())
        if not matches:
            return ""
        matches = self.get_original_candidates(matches, norm_cand)
        if len(matches) == 1 and matches[0] == name:
            return ""
        suggestion = " Did you mean:\n"
        suggestion += "\n".join(f"    {match}" for match in matches)
        return suggestion

    def find(self, name, candidates, max_matches=2):
        """Return a list of close matches to `name` from `candidates`."""
        if not name or not candidates:
            return []
        cutoff = self._calculate_cutoff(name)
        return difflib.get_close_matches(name, candidates, n=max_matches, cutoff=cutoff)

    @staticmethod
    def _calculate_cutoff(string, min_cutoff=0.5, max_cutoff=0.85, step=0.03):
        """The longer the string the bigger required cutoff."""
        cutoff = min_cutoff + len(string) * step
        return min(cutoff, max_cutoff)

    @staticmethod
    def get_original_candidates(candidates, norm_candidates):
        """Map found normalized candidates to unique original candidates."""
        return sorted(list(set(c for cand in candidates for c in norm_candidates[cand])))

    @staticmethod
    def get_normalized_candidates(candidates):
        norm_cand = {cand.lower(): [cand] for cand in candidates}
        # most popular typos
        norm_cand["align"] = ["AlignSettingsSection", "AlignVariablesSection"]
        norm_cand["normalize"] = [
            "NormalizeAssignments",
            "NormalizeNewLines",
            "NormalizeSectionHeaderName",
            "NormalizeSeparators",
            "NormalizeSettingName",
        ]
        norm_cand["order"] = ["OrderSettings", "OrderSettingsSection"]
        norm_cand["alignsettings"] = ["AlignSettingsSection"]
        norm_cand["alignvariables"] = ["AlignVariablesSection"]
        norm_cand["assignmentnormalizer"] = ["NormalizeAssignments"]
        return norm_cand


class ModelWriter(ModelVisitor):
    def __init__(self, output, newline):
        self.writer = file_writer(output, newline=newline)
        self.close_writer = True

    def write(self, model):
        try:
            self.visit(model)
        finally:
            if self.close_writer:
                self.writer.close()

    def visit_Statement(self, statement):  # noqa
        for token in statement.tokens:
            self.writer.write(token.value)


class TestTemplateFinder(ast.NodeVisitor):
    def __init__(self):
        self.templated = False

    def visit_TestTemplate(self, node):  # noqa
        if node.value:
            self.templated = True


def is_suite_templated(node):
    template_finder = TestTemplateFinder()
    template_finder.visit(node)
    return template_finder.templated


def is_blank_multiline(statements):
    return (
        statements[0].type == Token.CONTINUATION
        and len(statements) == 3
        and statements[1].type == "ARGUMENT"
        and not statements[1].value
    )
