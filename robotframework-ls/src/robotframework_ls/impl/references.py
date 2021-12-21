from typing import List

from robocorp_ls_core.lsp import LocationTypedDict
from robotframework_ls.impl.protocols import ICompletionContext


def references(
    completion_context: ICompletionContext, include_declaration: bool
) -> List[LocationTypedDict]:
    from robotframework_ls.impl.protocols import IKeywordFound
    from robocorp_ls_core import uris
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    ret: List[LocationTypedDict] = []
    current_keyword_definition_and_usage_info = (
        completion_context.get_current_keyword_definition_and_usage_info()
    )
    if current_keyword_definition_and_usage_info is not None:
        completion_context.monitor.check_cancelled()
        keyword_definition, usage_info = current_keyword_definition_and_usage_info

        keyword_found: IKeywordFound = keyword_definition.keyword_found

        normalized_name = normalize_robot_name(keyword_found.keyword_name)
        # Ok, we have the keyword definition, now, we must actually look for the
        # references...

    # ret.append(
    #     {
    #         "uri": uris.from_fs_path(r"X:\vscode-robot\local_test\Example\tasks.robot"),
    #         "range": {
    #             "start": {"line": 2, "character": 0},
    #             "end": {"line": 2, "character": 0},
    #         },
    #     }
    # )
    return ret
