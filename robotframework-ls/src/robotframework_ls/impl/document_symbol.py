from typing import List

from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.lsp import DocumentSymbolTypedDict, SymbolKind


def collect_children(ast) -> List[DocumentSymbolTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robot.api import Token  # noqa
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

    token = ast.header.get_token(header_token_type)
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


def document_symbol(
    completion_context: ICompletionContext
) -> List[DocumentSymbolTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robot.api import Token  # noqa

    ret: List[DocumentSymbolTypedDict] = []
    ast = completion_context.get_ast()

    for node_info in ast_utils.iter_all_nodes(ast, recursive=False):
        classname = node_info.node.__class__.__name__

        if classname == "SettingSection":
            create_section_doc_symbol(
                ret, node_info.node, Token.SETTING_HEADER, SymbolKind.Namespace
            )

        elif classname == "VariableSection":
            create_section_doc_symbol(
                ret, node_info.node, Token.VARIABLE_HEADER, SymbolKind.Namespace
            )

        elif classname == "TestCaseSection":
            create_section_doc_symbol(
                ret, node_info.node, Token.TESTCASE_HEADER, SymbolKind.Namespace
            )

        elif classname == "KeywordSection":
            create_section_doc_symbol(
                ret, node_info.node, Token.KEYWORD_HEADER, SymbolKind.Namespace
            )

    return ret
