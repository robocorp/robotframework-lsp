from typing import List

from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.lsp import DocumentSymbolTypedDict, SymbolKind


def collect_children(ast) -> List[DocumentSymbolTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robot.api import Token
    from robotframework_ls.impl.ast_utils import create_range_from_token

    ret: List[DocumentSymbolTypedDict] = []

    for node_info in ast_utils.iter_nodes(
        ast, accept_class=("Keyword", "TestCase", "Variable")
    ):
        node = node_info.node
        classname = node.__class__.__name__
        if classname == "Keyword":
            token = node.header.get_token(Token.KEYWORD_NAME)
            symbol_range = create_range_from_token(token)
            doc_symbol: DocumentSymbolTypedDict = {
                "name": str(token),
                "kind": SymbolKind.Function,
                "range": symbol_range,
                "selectionRange": symbol_range,
            }
            ret.append(doc_symbol)

        elif classname == "TestCase":
            token = node.header.get_token(Token.TESTCASE_NAME)
            symbol_range = create_range_from_token(token)
            doc_symbol = {
                "name": str(token),
                "kind": SymbolKind.Class,
                "range": symbol_range,
                "selectionRange": symbol_range,
            }
            ret.append(doc_symbol)

        elif classname == "Variable":
            token = node.get_token(Token.VARIABLE)
            symbol_range = create_range_from_token(token)
            doc_symbol = {
                "name": str(token),
                "kind": SymbolKind.Variable,
                "range": symbol_range,
                "selectionRange": symbol_range,
            }
            ret.append(doc_symbol)

    return ret


def create_section_doc_symbol(
    ret: List[DocumentSymbolTypedDict], ast, header_token_type, symbol_kind
):
    from robotframework_ls.impl.ast_utils import create_range_from_token

    if not isinstance(header_token_type, tuple):
        header_token_type = (header_token_type,)

    for t in header_token_type:
        token = ast.header.get_token(t)
        if token is not None:
            symbol_range = create_range_from_token(token)
            doc_symbol: DocumentSymbolTypedDict = {
                "name": str(token).replace("*", "").strip(),
                "kind": symbol_kind,
                "range": symbol_range,
                "selectionRange": symbol_range,
                "children": collect_children(ast),
            }
            ret.append(doc_symbol)
            break


def document_symbol(
    completion_context: ICompletionContext,
) -> List[DocumentSymbolTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robot.api import Token

    ret: List[DocumentSymbolTypedDict] = []
    ast = completion_context.get_ast()

    for node_info in ast_utils.iter_nodes(ast, "SettingSection"):
        create_section_doc_symbol(
            ret, node_info.node, Token.SETTING_HEADER, SymbolKind.Namespace
        )

    for node_info in ast_utils.iter_nodes(ast, "VariableSection"):
        create_section_doc_symbol(
            ret, node_info.node, Token.VARIABLE_HEADER, SymbolKind.Namespace
        )

    for node_info in ast_utils.iter_nodes(ast, "TestCaseSection"):
        create_section_doc_symbol(
            ret,
            node_info.node,
            (Token.TESTCASE_HEADER, getattr(Token, "TASK_HEADER", None)),
            SymbolKind.Namespace,
        )

    for node_info in ast_utils.iter_nodes(ast, "KeywordSection"):
        create_section_doc_symbol(
            ret, node_info.node, Token.KEYWORD_HEADER, SymbolKind.Namespace
        )

    return ret
