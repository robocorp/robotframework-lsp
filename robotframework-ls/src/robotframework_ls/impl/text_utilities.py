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
def normalize_robot_name(text):
    return text.lower().replace("_", "").replace(" ", "")


def is_variable_text(text: str) -> bool:
    from robotframework_ls.impl import robot_constants

    for p in robot_constants.VARIABLE_PREFIXES:
        if text.startswith(p + "{") and text.endswith("}"):
            return True
    return False


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


def matches_robot_keyword(keyword_name_call_text, keyword_name, _re_cache={}):
    """
    Checks if a given text matches a given keyword.

    Note: both should be already normalized.
    Note: should NOT be called if keyword does not have '{' in it.

    :param str keyword_name_call_text:
        The call that has resolved variables.

    :param str keyword_name:
        The keyword (which has variables -- i.e.: '{').
    """

    try:
        compiled = _re_cache[keyword_name]
    except KeyError:
        from robotframework_ls.impl import ast_utils
        import re

        try:
            tokenized_vars = ast_utils.tokenize_variables_from_name(keyword_name)
        except:
            regexp = [re.escape(keyword_name)]
        else:
            regexp = []
            for t in tokenized_vars:
                if t.type == t.VARIABLE:
                    regexp.append("(.*)")
                else:
                    regexp.append(re.escape(t.value))

        regexp.append("$")

        regexp = "".join(regexp)
        _re_cache[keyword_name] = re.compile(regexp)
        compiled = _re_cache[keyword_name]

    return compiled.match(keyword_name_call_text)


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
