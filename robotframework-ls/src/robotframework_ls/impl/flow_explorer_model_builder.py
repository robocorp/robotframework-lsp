from robotframework_ls.impl.protocols import ICompletionContext, IKeywordFound, INode
from typing import List, Any, Dict, Tuple
import os
from robocorp_ls_core.basic import isinstance_name


def _compute_suite_name(completion_context: ICompletionContext) -> str:
    suite_name = os.path.splitext(os.path.basename(completion_context.doc.uri))[0]
    suite_name = suite_name.title()
    return suite_name


def build_flow_explorer_model(completion_contexts: List[ICompletionContext]) -> dict:
    from robotframework_ls.impl import ast_utils

    suites: list = []
    model: dict = {"suites": suites}

    for completion_context in completion_contexts:
        ast = completion_context.get_ast()

        # Uncomment to print ast.
        ast_utils.print_ast(ast)

        if ast:
            suite_name = _compute_suite_name(completion_context)
            tasks: list = []
            keywords: list = []
            suite = {
                "type": "suite",
                "name": suite_name,
                "source": completion_context.doc.uri,
                "tasks": tasks,
                "keywords": keywords,
                "setup": None,
                "teardown": None,
            }
            suites.append(suite)

            for test in ast_utils.iter_tests(ast):
                test_name = f"{test.node.name} ({suite_name.lower()})"
                test_body: list = []
                test_info = {
                    "type": "task",
                    "name": test_name,
                    "doc": "",
                    "setup": None,
                    "teardown": None,
                    "body": test_body,
                }
                tasks.append(test_info)
                for node_info in ast_utils.iter_all_nodes(test.node, recursive=False):
                    _build_hierarchy(
                        completion_context,
                        node_info.stack,
                        node_info.node,
                        suite_name,
                        test_body,
                        {},
                    )
            for user_keyword in ast_utils.iter_keywords(ast):
                user_keyword_name = f"{user_keyword.node.name} ({suite_name.lower()})"
                user_keyword_body: list = []
                user_keyword_info = {
                    "type": "user-keyword",
                    "name": user_keyword_name,
                    "doc": "",
                    "body": user_keyword_body,
                }

                keywords.append(user_keyword_info)
                for node_info in ast_utils.iter_all_nodes(
                    user_keyword.node, recursive=False
                ):
                    _build_hierarchy(
                        completion_context,
                        node_info.stack,
                        node_info.node,
                        suite_name,
                        user_keyword_body,
                        {},
                    )

    if len(suites) == 1:
        # Special case (for now): If we only have one suite make it top-level
        return suites[0]
    return model


def _build_hierarchy(
    completion_context: ICompletionContext,
    curr_stack: Tuple[INode, ...],
    curr_ast: Any,
    suite_name: str,
    parent_body: List[Any],
    memo: dict,
):
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl import ast_utils_keyword_usage
    from robotframework_ls.impl.find_definition import find_keyword_definition
    from robotframework_ls.impl.protocols import TokenInfo

    if ast_utils.is_keyword_usage_node(curr_ast):
        keyword_usage_handler = ast_utils_keyword_usage.obtain_keyword_usage_handler(
            curr_stack, curr_ast, recursive=True
        )
        if keyword_usage_handler is not None:
            for keyword_usage in keyword_usage_handler.iter_keyword_usages_from_node():
                keyword_body: list = []
                keyword_usage_node: Any = keyword_usage.node

                if isinstance_name(keyword_usage_node, "KeywordCall"):
                    keyword = {
                        "type": "keyword",
                        "subtype": "KEYWORD",
                        "assign": keyword_usage_node.assign,
                        "args": keyword_usage_node.args,
                        "body": keyword_body,
                    }
                    parent_body.append(keyword)

                    # Now, we need to follow the keyword and build its own structure
                    token_info = TokenInfo(
                        keyword_usage.stack, keyword_usage.node, keyword_usage.token
                    )
                    definitions = find_keyword_definition(
                        completion_context.create_copy_with_selection(
                            keyword_usage.token.lineno - 1,
                            keyword_usage.token.col_offset,
                        ),
                        token_info,
                    )

                    # Fallback name if we don't know where it's defined.
                    keyword["name"] = f"{keyword_usage_node.keyword}"
                    if definitions:
                        # Use the first one
                        definition = next(iter(definitions))
                        keyword_found: IKeywordFound = definition.keyword_found
                        if keyword_found.library_name:
                            keyword[
                                "name"
                            ] = f"{keyword_usage_node.keyword} ({keyword_found.library_name.lower()})"
                        elif keyword_found.resource_name:
                            keyword[
                                "name"
                            ] = f"{keyword_usage_node.keyword} ({keyword_found.resource_name.lower()})"

                        # If it was found in a library we don't recurse anymore.
                        keyword_ast = keyword_found.keyword_ast
                        if keyword_ast is None:
                            continue
                        definition_completion_context = keyword_found.completion_context
                        if definition_completion_context is None:
                            continue

                        suite_name = _compute_suite_name(definition_completion_context)
                        # Ok, it isn't a library keyword (as we have its AST). Keep recursing.
                        for node_info in ast_utils.iter_all_nodes(
                            keyword_ast, recursive=False
                        ):
                            _build_hierarchy(
                                definition_completion_context,
                                node_info.stack,
                                node_info.node,
                                suite_name,
                                keyword_body,
                                memo,
                            )
                elif isinstance_name(keyword_usage_node, "Teardown") or isinstance_name(
                    keyword_usage_node, "Setup"
                ):
                    keyword = {
                        "type": "keyword",
                        "subtype": "KEYWORD",
                        "args": keyword_usage_node.args,
                        "name": keyword_usage_node.name,
                    }
                    parent_body.append(keyword)
    elif isinstance_name(curr_ast, "If"):
        if_body: list = []
        if_info: Dict[str, Any] = {"type": "if", "body": if_body}
        parent_body.append(if_info)

        condition = " ".join(
            str(tok) for tok in ast_utils.iter_argument_tokens(curr_ast.header)
        )
        if_branch_body: list = []
        if_branch_info: Dict[str, Any] = {
            "type": "if-branch",
            "condition": condition,
            "body": if_branch_body,
        }
        if_body.append(if_branch_info)
        for body_ast in curr_ast.body:
            _build_hierarchy(
                completion_context,
                curr_stack + (curr_ast,),
                body_ast,
                suite_name,
                if_branch_body,
                memo,
            )

        orelse = curr_ast.orelse

        def explore_elseifs(elseifbranch):
            if elseifbranch and isinstance_name(elseifbranch.header, "ElseIfHeader"):
                condition = " ".join(
                    str(tok)
                    for tok in ast_utils.iter_argument_tokens(elseifbranch.header)
                )
                else_if_body: list = []
                else_if_info: Dict[str, Any] = {
                    "type": "else-if-branch",
                    "condition": condition,
                    "body": else_if_body,
                }

                if_body.append(else_if_info)
                for body_ast in elseifbranch.body:
                    _build_hierarchy(
                        completion_context,
                        curr_stack + (elseifbranch,),
                        body_ast,
                        suite_name,
                        else_if_body,
                        memo,
                    )
                elseifbranch = elseifbranch.orelse
                if elseifbranch and isinstance_name(
                    elseifbranch.header, "ElseIfHeader"
                ):
                    explore_elseifs(elseifbranch)

        explore_elseifs(orelse)

        # To finish, handle the orelse.
        if orelse:
            orelse_body: list = []
            orelse_info: Dict[str, Any] = {
                "type": "else-branch",
                "body": orelse_body,
            }
            if_body.append(orelse_info)
            for body_ast in orelse.body:
                _build_hierarchy(
                    completion_context,
                    curr_stack + (orelse,),
                    body_ast,
                    suite_name,
                    orelse_body,
                    memo,
                )
    elif isinstance_name(curr_ast, "For"):
        for_body: list = []
        for_info: Dict[str, Any] = {
            "type": "for",
            "kind": curr_ast.flavor,
            "values": list(curr_ast.values),
            "variables": list(curr_ast.variables),
            "body": for_body,
        }
        parent_body.append(for_info)
        for body_ast in curr_ast.body:
            _build_hierarchy(
                completion_context,
                curr_stack + (curr_ast,),
                body_ast,
                suite_name,
                for_body,
                memo,
            )
    elif isinstance_name(curr_ast, "While"):
        condition = " ".join(
            str(tok) for tok in ast_utils.iter_argument_tokens(curr_ast.header)
        )
        while_body: list = []
        while_info: Dict[str, Any] = {
            "type": "while",
            "condition": condition,
            "body": while_body,
        }
        parent_body.append(while_info)
        for body_ast in curr_ast.body:
            _build_hierarchy(
                completion_context,
                curr_stack + (curr_ast,),
                body_ast,
                suite_name,
                while_body,
                memo,
            )
    elif isinstance_name(curr_ast, "Try"):
        try_body: list = []
        try_info: Dict[str, Any] = {
            "type": "try",
            "body": try_body,
        }
        parent_body.append(try_info)
        try_branch_body: list = []
        try_branch_info: Dict[str, Any] = {
            "type": "try-branch",
            "body": try_branch_body,
        }
        try_body.append(try_branch_info)

        for body_ast in curr_ast.body:
            _build_hierarchy(
                completion_context,
                curr_stack + (curr_ast,),
                body_ast,
                suite_name,
                try_branch_body,
                memo,
            )

        def explore_try(ast):
            if ast:
                next_type = None
                if isinstance_name(ast.header, "ExceptHeader"):
                    next_type = "except-branch"
                elif isinstance_name(ast.header, "FinallyHeader"):
                    next_type = "finally-branch"
                elif isinstance_name(ast.header, "ElseHeader"):
                    next_type = "else-branch"
                if not next_type:
                    return
                next_branch_body: list = []
                next_branch_info: Dict[str, Any] = {
                    "type": next_type,
                    "body": next_branch_body,
                }
                for body_ast in ast.body:
                    _build_hierarchy(
                        completion_context,
                        curr_stack + (ast,),
                        body_ast,
                        suite_name,
                        next_branch_body,
                        memo,
                    )
                try_body.append(next_branch_info)
                if ast.next:
                    explore_try(ast.next)

        explore_try(curr_ast.next)
    elif isinstance_name(curr_ast, "Break"):
        break_info: Dict[str, Any] = {
            "type": "break",
        }
        parent_body.append(break_info)
    elif isinstance_name(curr_ast, "Continue"):
        continue_info: Dict[str, Any] = {
            "type": "continue",
        }
        parent_body.append(continue_info)
    elif isinstance_name(curr_ast, "ReturnStatement"):
        return_info: Dict[str, Any] = {
            "type": "return",
        }
        parent_body.append(return_info)
