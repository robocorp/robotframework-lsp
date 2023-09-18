from collections import defaultdict

from robot.api.parsing import Token
from robot.parsing.model import Statement

from robotidy.disablers import skip_section_if_disabled
from robotidy.exceptions import InvalidParameterValueError
from robotidy.transformers import Transformer
from robotidy.utils import is_blank_multiline, left_align, round_to_four, tokens_by_lines


class AlignVariablesSection(Transformer):
    """
    Align variables in ``*** Variables ***`` section to columns.

    Following code:

    ```robotframework
    *** Variables ***
    ${VAR}  1
    ${LONGER_NAME}  2
    &{MULTILINE}  a=b
    ...  b=c
    ```

    will be transformed to:

    ```robotframework
    *** Variables ***
    ${VAR}          1
    ${LONGER_NAME}  2
    &{MULTILINE}    a=b
    ...             b=c
    ```

    You can configure how many columns should be aligned to longest token in given column. The remaining columns
    will use fixed length separator length ``--spacecount``. By default only first two columns are aligned.
    To align first three columns:

    ```console
    robotidy --transform AlignVariablesSection:up_to_column=3
    ```

    To align all columns set ``up_to_column`` to 0.
    """

    def __init__(self, up_to_column: int = 2, skip_types: str = "", min_width: int = None, fixed_width: int = None):
        super().__init__()
        self.up_to_column = up_to_column - 1
        self.min_width = min_width
        self.fixed_width = fixed_width
        self.skip_types = self.parse_skip_types(skip_types)

    def parse_skip_types(self, skip_types):
        allow_types = {"dict": "&", "list": "@", "scalar": "$"}
        ret = set()
        if not skip_types:
            return ret
        for skip_type in skip_types.split(","):
            if skip_type not in allow_types:
                raise InvalidParameterValueError(
                    self.__class__.__name__,
                    "skip_type",
                    skip_type,
                    "Variable types should be provided in comma separated list:\nskip_type=dict,list,scalar",
                )
            ret.add(allow_types[skip_type])
        return ret

    def should_parse(self, node):
        if not node.name:
            return True
        return node.name[0] not in self.skip_types

    @skip_section_if_disabled
    def visit_VariableSection(self, node):  # noqa
        statements = []
        for child in node.body:
            if self.disablers.is_node_disabled(child):
                statements.append(child)
            elif child.type in (Token.EOL, Token.COMMENT):
                statements.append(left_align(child))
            elif self.should_parse(child):
                statements.append(list(tokens_by_lines(child)))
            else:
                statements.append(child)
        nodes_to_be_aligned = [st for st in statements if isinstance(st, list)]
        if not nodes_to_be_aligned:
            return node
        look_up = self.create_look_up(nodes_to_be_aligned)  # for every col find longest value
        node.body = self.align_rows(statements, look_up)
        return node

    def align_rows(self, statements, look_up):
        aligned_statements = []
        for st in statements:
            if not isinstance(st, list):
                aligned_statements.append(st)
                continue
            aligned_statement = []
            for line in st:
                if is_blank_multiline(line):
                    line[-1].value = line[-1].value.lstrip(" \t")  # normalize eol from '  \n' to '\n'
                    aligned_statement.extend(line)
                    continue
                up_to = self.up_to_column if self.up_to_column != -1 else len(line) - 2
                for index, token in enumerate(line[:-2]):
                    aligned_statement.append(token)
                    separator = self.calc_separator(index, up_to, token, look_up)
                    aligned_statement.append(Token(Token.SEPARATOR, separator))
                last_token = line[-2]
                # remove leading whitespace before token
                last_token.value = last_token.value.strip() if last_token.value else last_token.value
                aligned_statement.append(last_token)
                aligned_statement.append(line[-1])  # eol
            aligned_statements.append(Statement.from_tokens(aligned_statement))
        return aligned_statements

    def calc_separator(self, index, up_to, token, look_up):
        if index < up_to:
            if self.fixed_width:
                return max(self.fixed_width - len(token.value), self.formatting_config.space_count) * " "
            return (look_up[index] - len(token.value) + 4) * " "
        else:
            return self.formatting_config.space_count * " "

    def create_look_up(self, statements):
        look_up = defaultdict(int)
        for st in statements:
            for line in st:
                up_to = self.up_to_column if self.up_to_column != -1 else len(line)
                for index, token in enumerate(line[:up_to]):
                    look_up[index] = max(look_up[index], len(token.value))
        if self.min_width:
            look_up = {index: max(length, self.min_width - 4) for index, length in look_up.items()}
        return {index: round_to_four(length) for index, length in look_up.items()}
