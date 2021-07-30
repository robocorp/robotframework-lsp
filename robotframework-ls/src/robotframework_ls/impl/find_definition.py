import re
from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IDefinition,
    TokenInfo,
    IKeywordDefinition,
)
from robocorp_ls_core.protocols import check_implements
from typing import Optional, Sequence

_RF_VARIABLE = re.compile(r"([$|&|@]{[\w\s]+})")

class _DefinitionFromKeyword(object):
    def __init__(self, keyword_found):
        """
        :param IKeywordFound keyword_found:
        """
        self.keyword_found = keyword_found
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

    def __typecheckself__(self) -> None:
        _: IKeywordDefinition = check_implements(self)


class _DefinitionFromLibrary(object):
    def __init__(self, library_doc):
        """
        :param LibraryDoc library_info:
        """
        self.keyword_name = ""
        self.library_doc = library_doc
        self.source = library_doc.source
        # Note: line/offsets 0-based.
        self.lineno = 0
        self.end_lineno = 0
        self.col_offset = 0
        self.end_col_offset = 0

    def __str__(self):
        return "DefinitionFromLibrary[%s]" % (self.source,)

    __repr__ = __str__

    def __typecheckself__(self) -> None:
        _: IDefinition = check_implements(self)


class _DefinitionFromResource(object):
    def __init__(self, resource_doc):
        """
        :param RobotDocument resource_doc:
        """
        from robocorp_ls_core import uris

        self.keyword_name = ""
        self.resource_doc = resource_doc
        self.source = uris.to_fs_path(resource_doc.uri)
        # Note: line/offsets 0-based.
        self.lineno = 0
        self.end_lineno = 0
        self.col_offset = 0
        self.end_col_offset = 0

    def __str__(self):
        return "DefinitionFromResource[%s]" % (self.source,)

    __repr__ = __str__

    def __typecheckself__(self) -> None:
        _: IDefinition = check_implements(self)


class _DefinitionFromVariableImport(object):
    def __init__(self, variables_doc):
        """
        :param RobotDocument variables_doc:
        """
        from robocorp_ls_core import uris

        self.keyword_name = ""
        self.variables_doc = variables_doc
        self.source = uris.to_fs_path(variables_doc.uri)
        # Note: line/offsets 0-based.
        self.lineno = 0
        self.end_lineno = 0
        self.col_offset = 0
        self.end_col_offset = 0

    def __str__(self):
        return "DefinitionFromVariableImport[%s]" % (self.source,)

    __repr__ = __str__

    def __typecheckself__(self) -> None:
        _: IDefinition = check_implements(self)


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

    def __typecheckself__(self) -> None:
        _: IDefinition = check_implements(self)


class IDefinitionsCollector(object):
    def accepts(self, keyword_name):
        pass

    def on_keyword(self, keyword_found):
        pass


class _FindDefinitionKeywordCollector(IDefinitionsCollector):
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


class _FindDefinitionVariablesCollector(IDefinitionsCollector):
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


def find_keyword_definition(
    completion_context: ICompletionContext, token_info: TokenInfo
) -> Optional[Sequence[IKeywordDefinition]]:
    """
    Find a definition only considering Keywords.
    
    The token info must be already computed and must match the completion
    context location.
    """
    from robotframework_ls.impl.collect_keywords import collect_keywords
    from robotframework_ls.impl import ast_utils

    token = ast_utils.get_keyword_name_token(token_info.node, token_info.token)
    if token is not None:
        collector = _FindDefinitionKeywordCollector(token.value)
        collect_keywords(completion_context, collector)
        return collector.matches
    return None


def find_definition(completion_context: ICompletionContext) -> Sequence[IDefinition]:
    """
    :note:
        Definitions may be found even if a given source file no longer exists
        at this place (callers are responsible for validating entries).
    """
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.string_matcher import RobotStringMatcher
    from robotframework_ls.impl.variable_completions import collect_variables

    token_info = completion_context.get_current_token()

    if token_info is not None:
        matches = find_keyword_definition(completion_context, token_info)
        if matches is not None:
            return matches

        token = ast_utils.get_library_import_name_token(
            token_info.node, token_info.token
        )
        if token is not None:
            libspec_manager = completion_context.workspace.libspec_manager
            completion_context.check_cancelled()
            library_doc = libspec_manager.get_library_info(
                completion_context.token_value_resolving_variables(token),
                create=True,
                current_doc_uri=completion_context.doc.uri,
            )
            if library_doc is not None:
                definition = _DefinitionFromLibrary(library_doc)
                return [definition]

        token = ast_utils.get_resource_import_name_token(
            token_info.node, token_info.token
        )
        if token is not None:
            completion_context.check_cancelled()
            resource_import_as_doc = completion_context.get_resource_import_as_doc(
                token_info.node
            )
            if resource_import_as_doc is not None:
                return [_DefinitionFromResource(resource_import_as_doc)]

        token = ast_utils.get_variables_import_name_token(
            token_info.node, token_info.token
        )
        if token is not None:
            completion_context.check_cancelled()
            variable_import_as_doc = completion_context.get_variable_import_as_doc(
                token_info.node
            )
            if variable_import_as_doc is not None:
                return [_DefinitionFromVariableImport(variable_import_as_doc)]

    token_info = completion_context.get_current_variable()
    if token_info is not None:

        token = token_info.token
        value = token.value
        match = next(iter(_RF_VARIABLE.findall(value)), value)
        collector = _FindDefinitionVariablesCollector(
            completion_context.sel, token, RobotStringMatcher(match)
        )
        collect_variables(completion_context, collector)
        return collector.matches

    return []
