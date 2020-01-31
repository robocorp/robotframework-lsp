from robotframework_ls import _utils
from robotframework_ls.python_ls import PythonLanguageServer


LINT_DEBOUNCE_S = 0.5  # 500 ms


class RobotFrameworkLanguageServer(PythonLanguageServer):
    @_utils.debounce(LINT_DEBOUNCE_S, keyed_by="doc_uri")
    def lint(self, doc_uri, is_saved):
        from robotframework_ls.ext.errors import collect_errors

        # Since we're debounced, the document may no longer be open
        workspace = self._match_uri_to_workspace(doc_uri)
        if doc_uri in workspace.documents:
            document = workspace.get_document(doc_uri)
            errors = collect_errors(document.source)
            workspace.publish_diagnostics(
                doc_uri, [error.to_lsp_diagnostic() for error in errors]
            )
