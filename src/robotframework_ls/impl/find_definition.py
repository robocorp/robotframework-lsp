class IDefinition(object):

    keyword_name = ""

    # Note: Could be None (i.e.: we found it in a library spec file which doesn't have the source).
    source = ""

    # Note: Could be None (i.e.: we found it in a library spec file which doesn't have the lineno).
    lineno = -1

    # Note: Could be None (i.e.: we found it in a library spec file which doesn't have the lineno).
    end_lineno = -1

    col_offset = -1

    end_col_offset = -1


class _Definition(object):
    def __init__(self, keyword_found):
        """
        :param IKeywordFound keyword_found:
        """
        self.keyword_name = keyword_found.keyword_name
        self.source = keyword_found.source
        self.lineno = keyword_found.lineno
        self.end_lineno = keyword_found.end_lineno
        self.col_offset = keyword_found.col_offset
        self.end_col_offset = keyword_found.end_col_offset

    def __str__(self):
        return "Definition[%s, %s:%s]" % (self.keyword_name, self.source, self.lineno)

    __repr__ = __str__


class _Collector(object):
    def __init__(self, match_name):
        from robotframework_ls.impl.string_matcher import RobotStringMatcher

        self.match_name = match_name
        self.matches = []
        self._matcher = RobotStringMatcher(self.match_name)

    def accepts(self, keyword_name):
        return self._matcher.is_keyword_name_match(keyword_name)

    def on_keyword(self, keyword_found):
        definition = _Definition(keyword_found)
        self.matches.append(definition)


def find_definition(completion_context):
    """
    :param CompletionContext completion_context:
    :rtype: list(IDefinition)
    
    :note:
        Definitions may be found even if a given source file no longer exists
        at this place (callers are responsible for validating entries).
    """
    from robotframework_ls.impl.collect_keywords import collect_keywords
    from robotframework_ls.impl import ast_utils

    token_info = completion_context.get_current_token()
    if token_info is not None and ast_utils.is_keyword_name_location(
        token_info.node, token_info.token
    ):
        token = token_info.token
        collector = _Collector(token.value)
        collect_keywords(completion_context, collector)

        return collector.matches

    return []
