class _KeywordsCollector(object):
    def __init__(self):
        self.name_to_keyword = {}

    def accepts(self, keyword_name):
        return True

    def on_keyword(self, keyword_found):
        """
        :param IKeywordFound keyword_found:
        """
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        self.name_to_keyword[
            normalize_robot_name(keyword_found.keyword_name)
        ] = keyword_found


def collect_analysis_errors(completion_context):
    from robotframework_ls.impl.collect_keywords import collect_keywords
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    from robotframework_ls.impl.ast_utils import create_error_from_node

    errors = []
    collector = _KeywordsCollector()
    collect_keywords(completion_context, collector)

    ast = completion_context.get_ast()
    for keyword_usage_info in ast_utils.iter_keyword_usage_tokens(ast):
        if (
            normalize_robot_name(keyword_usage_info.name)
            not in collector.name_to_keyword
        ):
            node = keyword_usage_info.node
            error = create_error_from_node(
                node,
                "Undefined keyword: %s." % (keyword_usage_info.name,),
                tokens=[keyword_usage_info.token],
            )
            errors.append(error)
    return errors
