from collections import defaultdict

from robot.api.parsing import Token
from robot.parsing.model import Statement

from robotidy.disablers import skip_section_if_disabled
from robotidy.transformers import Transformer
from robotidy.utils import is_blank_multiline, left_align, round_to_four, tokens_by_lines


class AlignSettingsSection(Transformer):
    """
    Align statements in ``*** Settings ***`` section to columns.

    Following code:

    ```robotframework
    *** Settings ***
    Library      SeleniumLibrary
    Library   Mylibrary.py
    Variables  variables.py
    Test Timeout  1 min
        # this should be left aligned
    ```

    will be transformed to:

    ```robotframework
    *** Settings ***
    Library         SeleniumLibrary
    Library         Mylibrary.py
    Variables       variables.py
    Test Timeout    1 min
    # this should be left aligned
    ```

    You can configure how many columns should be aligned to longest token in given column. The remaining columns
    will use fixed length separator length ``--spacecount``. By default only first two columns are aligned.
    To align first three columns:

    ```
    robotidy --transform AlignSettingsSection:up_to_column=3
    ```

    To align all columns set ``up_to_column`` to 0.

    Arguments inside keywords in Suite Setup, Suite Teardown, Test Setup and Test Teardown are indented by additional
    ``argument_indent`` (default ``4``) spaces:

    ```robotframework
    *** Settings ***
    Suite Setup         Start Session
    ...                     host=${IPADDRESS}
    ...                     user=${USERNAME}
    ...                     password=${PASSWORD}
    Suite Teardown      Close Session
    ```

    To disable it configure ``argument_indent`` with ``0``.

    Supports global formatting param ``--spacecount`` (for columns with fixed length).
    """

    TOKENS_WITH_ARGUMENTS = {
        Token.SUITE_SETUP,
        Token.SUITE_TEARDOWN,
        Token.TEST_SETUP,
        Token.TEST_TEARDOWN,
        Token.LIBRARY,
        Token.VARIABLES,
    }

    def __init__(self, up_to_column: int = 2, argument_indent: int = 4, min_width: int = None):
        super().__init__()
        self.up_to_column = up_to_column - 1
        self.argument_indent = argument_indent
        self.min_width = min_width

    @skip_section_if_disabled
    def visit_SettingSection(self, node):  # noqa
        statements = []
        for child in node.body:
            if self.disablers.is_node_disabled(child):
                statements.append(child)
            elif child.type in (Token.EOL, Token.COMMENT):
                statements.append(left_align(child))
            else:
                statements.append(list(tokens_by_lines(child)))
        nodes_to_be_aligned = [st for st in statements if isinstance(st, list)]
        if not nodes_to_be_aligned:
            return node
        look_up = self.create_look_up(nodes_to_be_aligned)  # for every col find longest value
        node.body = self.align_rows(statements, look_up)
        return node

    def should_indent_arguments(self, statement):
        statement_type = statement[0][0].type
        is_library = statement_type == Token.LIBRARY
        if is_library:
            return is_library, True
        return is_library, statement_type in self.TOKENS_WITH_ARGUMENTS

    def align_rows(self, statements, look_up):
        aligned_statements = []
        for st in statements:
            if not isinstance(st, list):
                aligned_statements.append(st)
                continue
            is_library, indent_args = self.should_indent_arguments(st)
            aligned_statement = []
            for line in st:
                if is_blank_multiline(line):
                    line[-1].value = line[-1].value.lstrip(" \t")  # normalize eol from '  \n' to '\n'
                    aligned_statement.extend(line)
                    continue
                indent_arg = indent_args and line[0].type == Token.CONTINUATION
                if indent_arg and is_library:
                    indent_arg = all(token.type != Token.WITH_NAME for token in line)
                up_to = self.up_to_column if self.up_to_column != -1 else len(line) - 2
                for index, token in enumerate(line[:-2]):
                    aligned_statement.append(token)
                    separator = self.calc_separator(index, up_to, indent_arg, token, look_up)
                    aligned_statement.append(Token(Token.SEPARATOR, separator))
                last_token = line[-2]
                # remove leading whitespace before token
                last_token.value = last_token.value.strip() if last_token.value else last_token.value
                aligned_statement.append(last_token)
                aligned_statement.append(line[-1])  # eol
            aligned_statements.append(Statement.from_tokens(aligned_statement))
        return aligned_statements

    def calc_separator(self, index, up_to, indent_arg, token, look_up):
        if index < up_to:
            if self.min_width:
                return max(self.min_width - len(token.value), self.formatting_config.space_count) * " "
            arg_indent = self.argument_indent if indent_arg else 0
            if indent_arg and index != 0:
                return (
                    max(
                        (look_up[index] - len(token.value) - arg_indent + 4),
                        self.formatting_config.space_count,
                    )
                    * " "
                )
            else:
                return (look_up[index] - len(token.value) + arg_indent + 4) * " "
        else:
            return self.formatting_config.space_count * " "

    def create_look_up(self, statements):
        look_up = defaultdict(int)
        for st in statements:
            is_doc = st[0][0].type == Token.DOCUMENTATION
            for line in st:
                if is_doc:
                    up_to = 1
                elif self.up_to_column != -1:
                    up_to = self.up_to_column
                else:
                    up_to = len(line)
                for index, token in enumerate(line[:up_to]):
                    look_up[index] = max(look_up[index], len(token.value))
        return {index: round_to_four(length) for index, length in look_up.items()}
