from functools import lru_cache
from robocorp_ls_core.robotframework_log import get_logger
import re
from typing import Sequence

log = get_logger(__name__)


class TextUtilities(object):
    def __init__(self, text):
        self.text = text

    def strip_leading_chars(self, c):
        if len(c) != 1:
            raise AssertionError('Expected "%s" to have size == 1' % (c,))
        text = self.text
        if len(text) == 0 or text[0] != c:
            return False
        for i, text_c in enumerate(text):
            if text_c != c:
                self.text = self.text[i:]
                return True

        else:
            # Consumed all chars
            self.text = ""
            return True

    def strip(self):
        self.text = self.text.strip()


# Note: this not only makes it faster, but also makes us use less memory as a
# way to reuse the same 'interned" strings.
@lru_cache(maxsize=2000)
def normalize_robot_name(text: str) -> str:
    return text.lower().replace("_", "").replace(" ", "")


def is_variable_text(text: str) -> bool:
    from robotframework_ls.impl import robot_constants

    for p in robot_constants.VARIABLE_PREFIXES:
        if text.startswith(p + "{") and text.endswith("}"):
            return True
    return False


@lru_cache(maxsize=1000)
def contains_variable_text(text: str) -> bool:
    if "{" not in text:
        return False

    from robotframework_ls.impl import ast_utils

    token = ast_utils.create_token(text)

    try:
        tokenized_vars = ast_utils.tokenize_variables(token)
        for v in tokenized_vars:
            if v.type == v.VARIABLE:
                return True

    except:
        log.debug("Error tokenizing to variables: %s", text)

    return False


@lru_cache(1000)
def matches_name_with_variables(name: str, name_with_variables: str) -> bool:
    """
    Checks if a given text matches a given keyword.

    Note: both should be already normalized.
    Note: should NOT be called if name_with_variables does not have '{' in it.

    :param name:
        The call that has resolved variables.
        i.e.: some call

    :param name_with_variables:
        The name which has variables.
        i.e.: some ${arg}
    """

    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.variable_resolve import extract_variable_base

    try:
        tokenized_vars = ast_utils.tokenize_variables_from_name(name_with_variables)
    except:
        regexp = [re.escape(name_with_variables)]
    else:
        regexp = []
        for t in tokenized_vars:
            if t.type == t.VARIABLE:
                variable_base = extract_variable_base(t.value)
                i = variable_base.find(":")
                if i > 0:
                    custom_regexp = variable_base[i + 1 :]
                    try:
                        pattern = _EmbeddedArgumentParser.format_custom_regexp(
                            f"{custom_regexp}"
                        )
                    except Exception:
                        log.exception(
                            f"Error formatting regexp: {custom_regexp} when matching: {name_with_variables}."
                        )
                        return False

                    regexp.append(f"({pattern})")

                else:
                    regexp.append("(.*?)")  # default pattern
            else:
                regexp.append(re.escape(t.value))

    regexp.append("$")

    pattern = "".join(regexp)
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except Exception:
        log.exception(
            f"Unable to compile regexp: {pattern} when matching: {name_with_variables}."
        )
        return False

    return bool(compiled.match(name))


class _EmbeddedArgumentParser:
    # Based on robot.running.arguments.embedded.EmbeddedArgumentParser
    _regexp_extension = re.compile(r"(?<!\\)\(\?.+\)")
    _regexp_group_start = re.compile(r"(?<!\\)\((.*?)\)")
    _escaped_curly = re.compile(r"(\\+)([{}])")
    _regexp_group_escape = r"(?:\1)"
    _default_pattern = ".*?"
    _variable_pattern = r"\$\{[^\}]+\}"

    @classmethod
    def format_custom_regexp(cls, pattern):
        for formatter in (
            cls._regexp_extensions_are_not_allowed,
            cls._make_groups_non_capturing,
            cls._unescape_curly_braces,
            cls._add_automatic_variable_pattern,
        ):
            pattern = formatter(pattern)
        return pattern

    @classmethod
    def _regexp_extensions_are_not_allowed(cls, pattern):
        if not cls._regexp_extension.search(pattern):
            return pattern
        raise RuntimeError(
            "Regexp extensions are not allowed in embedded " "arguments."
        )

    @classmethod
    def _make_groups_non_capturing(cls, pattern):
        return cls._regexp_group_start.sub(cls._regexp_group_escape, pattern)

    @classmethod
    def _unescape_curly_braces(cls, pattern):
        def unescaper(match):
            backslashes = len(match.group(1))
            return "\\" * (backslashes // 2 * 2) + match.group(2)

        return cls._escaped_curly.sub(unescaper, pattern)

    @classmethod
    def _add_automatic_variable_pattern(cls, pattern):
        return "%s|%s" % (pattern, cls._variable_pattern)


def iter_dotted_names(text: str):
    """
    list(iter_dotted_names("")) == []
    list(iter_dotted_names("a")) == []
    list(iter_dotted_names("a.b")) == [("a", "b")]
    list(iter_dotted_names(".a.b.")) == [
        ("", "a.b."),
        (".a", "b."),
        (".a.b", ""),
    ]
    list(iter_dotted_names("a.b.")) == [("a", "b."), ("a.b", "")]
    list(iter_dotted_names("a.b.c")) == [("a", "b.c"), ("a.b", "c")]
    """
    splitted = text.split(".")
    splitted_len = len(splitted)
    if splitted_len > 1:
        import io

        buf = io.StringIO()

        for i, name in enumerate(splitted[:-1]):
            if i > 0:
                buf.write(".")
            buf.write(name)
            remainder = ".".join(splitted[i + 1 :])
            head = buf.getvalue()
            yield head, remainder


_DEPRECATED_PATTERN = re.compile(r"^\*DEPRECATED(.*)\*(.*)")


def has_deprecated_text(docs: str) -> bool:
    if docs and "DEPRECATED" in docs:
        matched = _DEPRECATED_PATTERN.match(docs)
        return bool(matched)

    return False


def build_keyword_docs_with_signature(
    keyword_name: str,
    args: Sequence[str],  # tuple(x.original_arg for x in keyword_args)
    docs: str,
    docs_format: str,
):

    if docs_format == "markdown":
        # Multi-line approach (it's a bit too big -- maybe as an option?)
        # if docs_format == "markdown":
        #     arg_docs = "  \n&nbsp;&nbsp;&nbsp;&nbsp;".join(
        #         ("**" + (x.replace("*", "\\*") + "**") for x in args)
        #     )
        #     return f"**{keyword_name}**  \n&nbsp;&nbsp;&nbsp;&nbsp;{arg_docs}\n\n{docs}"

        if args:
            escaped_args = (x.replace("*", "\\*") for x in args)
            arg_docs = f'({", ".join(escaped_args)})'

        else:
            arg_docs = ""
        return f"**{keyword_name}{arg_docs}**\n\n{docs}"
    else:
        if args:
            arg_docs = f'({", ".join(args)})'

        else:
            arg_docs = ""

        return f"{keyword_name}{arg_docs}\n\n{docs}"


@lru_cache(maxsize=300)
def get_digest_from_string(s: str) -> str:
    import hashlib

    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:8]
