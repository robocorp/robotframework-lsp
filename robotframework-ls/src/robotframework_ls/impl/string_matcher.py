from robotframework_ls.impl.text_utilities import (
    normalize_robot_name,
    matches_name_with_variables,
)
from robotframework_ls.impl.protocols import IKeywordFound


class RobotStringMatcher(object):
    def __init__(self, filter_text):
        self.filter_text = normalize_robot_name(filter_text)
        self._has_variable = None

    def accepts(self, word):
        if not self.filter_text:
            return True
        return self.filter_text in normalize_robot_name(word)

    def accepts_keyword_name(self, word):
        if not self.filter_text:
            return True
        return self.filter_text in normalize_robot_name(word)

    def is_same_robot_name(self, word):
        return self.filter_text == normalize_robot_name(word)

    def is_keyword_name_match(self, keyword_name):
        normalized = normalize_robot_name(keyword_name)
        if self.filter_text == normalized:
            return True

        if "{" in normalized:
            return matches_name_with_variables(self.filter_text, normalized)

        return False

    def is_variable_name_match(self, variable_name):
        normalized = normalize_robot_name(variable_name)
        if self.filter_text == normalized:
            return True

        if "{" in normalized:
            if matches_name_with_variables(self.filter_text, normalized):
                return True

        if self._has_variable is None:
            from robotframework_ls.impl.variable_resolve import has_variable

            self._has_variable = has_variable(self.filter_text)

        if self._has_variable:
            # We need the other way around if the definition has variables.
            if matches_name_with_variables(normalized, self.filter_text):
                return True

        return False


class MatcherWithResourceOrLibraryName(RobotStringMatcher):
    def __init__(self, resource_or_library_name, qualifier):
        """
        :param resource_or_library_name str:
            The resource or library name to match (i.e.: BuiltIn, my_library).
        :param qualifier:
            The qualifier of the word to be matched in that library.
        """
        RobotStringMatcher.__init__(self, qualifier)
        self.resource_or_library_name = resource_or_library_name
        self.resource_or_library_name_normalized = normalize_robot_name(
            resource_or_library_name
        )

    def accepts_keyword(self, keyword_found: IKeywordFound):
        name = keyword_found.library_alias
        if name is None:
            name = keyword_found.resource_name or keyword_found.library_name

        if normalize_robot_name(name) == self.resource_or_library_name_normalized:
            return self.accepts_keyword_name(keyword_found.keyword_name)
        return False

    def is_keyword_match(self, keyword_found: IKeywordFound):
        name = keyword_found.library_alias
        if name is None:
            name = keyword_found.resource_name or keyword_found.library_name

        if normalize_robot_name(name) == self.resource_or_library_name_normalized:
            return self.is_keyword_name_match(keyword_found.keyword_name)
        return False


def build_matchers_with_resource_or_library_scope(token_str: str):
    """
    Given a string such as:

    'BuiltIn.Should Contain'

    it'll return:

    [MatcherWithResourceOrLibraryName('BuiltIn', 'Should Contain')]
    """
    from robotframework_ls.impl.text_utilities import iter_dotted_names

    resource_matchers = []
    for resource_or_library_name, qualifier in iter_dotted_names(token_str):
        resource_matchers.append(
            MatcherWithResourceOrLibraryName(resource_or_library_name, qualifier)
        )
    return resource_matchers
