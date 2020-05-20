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
        from robotframework_ls.impl.string_matcher import (
            build_matchers_with_resource_or_library_scope,
        )

        self.match_name = match_name
        self.matches = []

        self._matcher = RobotStringMatcher(match_name)
        self._scope_matchers = build_matchers_with_resource_or_library_scope(match_name)

    def accepts(self, keyword_name):
        return True

    def on_keyword(self, keyword_found):
        if self._matcher.is_keyword_name_match(keyword_found.keyword_name):
            definition = _Definition(keyword_found)
            self.matches.append(definition)
            return

        for matcher in self._scope_matchers:
            if matcher.is_keyword_match(keyword_found):
                definition = _Definition(keyword_found)
                self.matches.append(definition)
                return


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
    if token_info is not None:
        token = ast_utils.get_keyword_name_token(token_info.node, token_info.token)
        if token is not None:
            collector = _Collector(token.value)
            collect_keywords(completion_context, collector)

        return collector.matches

    return []
