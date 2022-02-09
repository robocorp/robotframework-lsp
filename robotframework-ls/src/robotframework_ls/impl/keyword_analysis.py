from robotframework_ls.impl.protocols import (
    IKeywordFound,
    KeywordUsageInfo,
    IKeywordArg,
)
from typing import Optional, List


class KeywordAnalysis:
    def __init__(self, keyword_found: IKeywordFound) -> None:

        self.keyword_found = keyword_found

        args = self._keyword_args = keyword_found.keyword_args

        self.found_star_arg: Optional[IKeywordArg] = None
        self.found_keyword_arg: Optional[IKeywordArg] = None
        self._star_arg_index = -1
        self._keyword_arg_index = -1

        for i, arg in enumerate(args):
            if arg.is_star_arg:
                self.found_star_arg = arg
                self._star_arg_index = i

            elif arg.is_keyword_arg:
                self.found_keyword_arg = arg
                self._keyword_arg_index = i

    def compute_active_parameter(
        self, usage_info: KeywordUsageInfo, lineno: int, col: int
    ) -> int:
        from robot.api import Token
        from robotframework_ls.impl.text_utilities import is_variable_text
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        active_parameter: int = 0
        # We need to find out the current arg/separator.
        after_last_arg: List[Token] = []
        usage_info_arg_tokens = []

        for token in usage_info.node.tokens:
            if token.type == Token.ARGUMENT:
                usage_info_arg_tokens.append(token)
                active_parameter += 1
                del after_last_arg[:]

            elif token.type in (Token.SEPARATOR, Token.EOL, Token.EOS):
                after_last_arg.append(token)
            else:
                # Keyword name token
                del after_last_arg[:]

            if token.lineno - 1 == lineno:
                if (token.end_col_offset - 1) >= col:
                    break

        if token.type == Token.ARGUMENT:
            active_parameter -= 1

        elif after_last_arg:
            # Check if we are in prev/next based on the number of spaces found
            # up to the current cursor position.
            # i.e.: in `Call  arg ` we still need to have an active_parameter == 0
            # i.e.: in `Call  arg  ` we need to have an active_parameter == 1
            whitespaces_found = []
            if token.lineno - 1 == lineno:
                if (token.end_col_offset - 1) <= col:
                    whitespaces_found.append(token.value)
                else:
                    whitespaces_found.append(
                        token.value[: -(token.end_col_offset - col)]
                    )
            s = "".join(whitespaces_found)
            if len(s) <= 1:
                active_parameter -= 1

        if active_parameter >= 0 and active_parameter < len(usage_info_arg_tokens):
            saw_eq = False
            for arg in usage_info_arg_tokens[:active_parameter]:
                saw_eq = "=" in arg.value
                if saw_eq:
                    break

            caller_arg_value = usage_info_arg_tokens[active_parameter].value
            definition_keyword_args = self._keyword_args
            # Now, it's also possible that we're dealing with an assign here... let's
            # see if this is the case.
            eq = caller_arg_value.find("=")
            if eq != -1:
                name = normalize_robot_name(caller_arg_value[:eq].strip())
                for i, keyword_arg in enumerate(definition_keyword_args):
                    arg_name = keyword_arg.original_arg
                    if is_variable_text(arg_name):
                        arg_name = arg_name[2:-1]
                    arg_name = normalize_robot_name(arg_name)
                    if name == arg_name:
                        active_parameter = i
                        break
                else:
                    # We do NOT have a match (match keyword arg if present...)
                    for i, arg in enumerate(definition_keyword_args):
                        if arg.is_keyword_arg:
                            active_parameter = i
                            break
                    else:
                        # This is actually off (error in call).
                        active_parameter = -1

            else:
                if saw_eq and self._keyword_arg_index >= 0:
                    return self._keyword_arg_index

                # Ok, does not have an assign, let's inspect the original signature
                # to detect where this should be put there (positional arg or
                # stararg).
                for i, arg in enumerate(definition_keyword_args):
                    if i == active_parameter:
                        break

                    if arg.is_star_arg:
                        active_parameter = i
                        break

                    if arg.is_keyword_arg:
                        # This is actually off (error in call).
                        active_parameter = -1
                        break

        return active_parameter
