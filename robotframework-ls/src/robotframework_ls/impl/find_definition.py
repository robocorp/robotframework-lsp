class IDefinition(object):

    keyword_name = ""  # Can be empty if it's not found as a keyword.

    # Note: Could be None (i.e.: we found it in a library spec file which doesn't have the source).
    source = ""

    # Note: Could be None (i.e.: we found it in a library spec file which doesn't have the lineno).
    lineno = -1

    # Note: Could be None (i.e.: we found it in a library spec file which doesn't have the lineno).
    end_lineno = -1

    col_offset = -1

    end_col_offset = -1


class _DefinitionFromKeyword(object):
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
        return "DefinitionFromKeyword[%s, %s:%s]" % (
            self.keyword_name,
            self.source,
            self.lineno,
        )

    __repr__ = __str__


class _DefinitionFromLibrary(object):
    def __init__(self, library_doc):
        """
        :param LibraryDoc library_info:
        """
        self.keyword_name = ""
        self.library_doc = library_doc
        self.source = library_doc.source
        self.lineno = 1
        self.end_lineno = 1
        self.col_offset = 1
        self.end_col_offset = 1

    def __str__(self):
        return "DefinitionFromLibrary[%s]" % (self.source,)

    __repr__ = __str__


class _DefinitionFromResource(object):
    def __init__(self, resource_doc):
        """
        :param RobotDocument resource_doc:
        """
        from robocorp_ls_core import uris

        self.keyword_name = ""
        self.resource_doc = resource_doc
        self.source = uris.to_fs_path(resource_doc.uri)
        self.lineno = 1
        self.end_lineno = 1
        self.col_offset = 1
        self.end_col_offset = 1

    def __str__(self):
        return "DefinitionFromResource[%s]" % (self.source,)

    __repr__ = __str__


class _DefinitionFromVariable(object):
    def __init__(self, variable_found):
        """
        :param IVariableFound variable_found:
        """
        self.variable_found = variable_found

        self.keyword_name = ""
        self.source = variable_found.source
        self.lineno = variable_found.lineno
        self.end_lineno = variable_found.end_lineno
        self.col_offset = variable_found.col_offset
        self.end_col_offset = variable_found.end_col_offset

    def __str__(self):
        return "_DefinitionFromVariable(%s[%s, %s:%s])" % (
            self.variable_found.__class__.__name__,
            self.variable_found.variable_name,
            self.source,
            self.lineno,
        )

    __repr__ = __str__


class _FindDefinitionKeywordCollector(object):
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
            definition = _DefinitionFromKeyword(keyword_found)
            self.matches.append(definition)
            return

        for matcher in self._scope_matchers:
            if matcher.is_keyword_match(keyword_found):
                definition = _DefinitionFromKeyword(keyword_found)
                self.matches.append(definition)
                return


class _FindDefinitionVariablesCollector(object):
    def __init__(self, sel, token, robot_string_matcher):
        self.matches = []
        self.sel = sel
        self.token = token
        self.matcher = robot_string_matcher

    def accepts(self, variable_name):
        return self.matcher.is_same_robot_name(variable_name)

    def on_variable(self, variable_found):
        definition = _DefinitionFromVariable(variable_found)
        self.matches.append(definition)


def find_definition(completion_context):
    """
    :param CompletionContext completion_context:
    :rtype: list(IDefinition)
    
    :note:
        Definitions may be found even if a given source file no longer exists
        at this place (callers are responsible for validating entries).
    """
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.collect_keywords import collect_keywords
    from robotframework_ls.impl.string_matcher import RobotStringMatcher
    from robotframework_ls.impl.variable_completions import collect_variables

    token_info = completion_context.get_current_token()
    if token_info is not None:
        token = ast_utils.get_keyword_name_token(token_info.node, token_info.token)
        if token is not None:
            collector = _FindDefinitionKeywordCollector(token.value)
            collect_keywords(completion_context, collector)
            return collector.matches

        token = ast_utils.get_library_import_name_token(
            token_info.node, token_info.token
        )
        if token is not None:
            libspec_manager = completion_context.workspace.libspec_manager
            library_doc = libspec_manager.get_library_info(
                token.value, create=True, current_doc_uri=completion_context.doc.uri
            )
            if library_doc is not None:
                definition = _DefinitionFromLibrary(library_doc)
                return [definition]

        token = ast_utils.get_resource_import_name_token(
            token_info.node, token_info.token
        )
        if token is not None:
            resource_import_as_doc = completion_context.get_resource_import_as_doc(
                token_info.node
            )
            if resource_import_as_doc is not None:
                return [_DefinitionFromResource(resource_import_as_doc)]

    token_info = completion_context.get_current_variable()
    if token_info is not None:

        token = token_info.token
        value = token.value

        collector = _FindDefinitionVariablesCollector(
            completion_context.sel, token, RobotStringMatcher(value)
        )
        collect_variables(completion_context, collector)
        return collector.matches

    return []
