class _KeywordsCollector(object):
    def __init__(self):
        self.name_to_keyword = {}
        self.names_with_variables = set()

    def accepts(self, keyword_name):
        return True

    def on_keyword(self, keyword_found):
        """
        :param IKeywordFound keyword_found:
        """
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        normalized_name = normalize_robot_name(keyword_found.keyword_name)
        self.name_to_keyword[normalized_name] = keyword_found

        if "{" in normalized_name:
            self.names_with_variables.add(normalized_name)

    def contains_keyword(self, normalized_keyword_name):
        from robotframework_ls.impl.text_utilities import matches_robot_keyword

        if normalized_keyword_name in self.name_to_keyword:
            return True

        # We do not have an exact match, still, we need to check if we may
        # have a match in keywords that accept variables.
        for name in self.names_with_variables:
            if matches_robot_keyword(normalized_keyword_name, name):
                return True

        return False


def collect_analysis_errors(completion_context):
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.ast_utils import create_error_from_node
    from robotframework_ls.impl.collect_keywords import collect_keywords
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    errors = []
    collector = _KeywordsCollector()
    collect_keywords(completion_context, collector)

    ast = completion_context.get_ast()
    for keyword_usage_info in ast_utils.iter_keyword_usage_tokens(ast):
        normalized_name = normalize_robot_name(keyword_usage_info.name)
        if not collector.contains_keyword(normalized_name):
            node = keyword_usage_info.node
            error = create_error_from_node(
                node,
                "Undefined keyword: %s." % (keyword_usage_info.name,),
                tokens=[keyword_usage_info.token],
            )
            errors.append(error)
    return errors
