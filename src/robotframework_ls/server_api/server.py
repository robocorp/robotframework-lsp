from robotframework_ls.python_ls import PythonLanguageServer
from robotframework_ls._utils import overrides
from robotframework_ls.robotframework_log import get_logger


log = get_logger(__name__)


class RobotFrameworkServerApi(PythonLanguageServer):
    """
    This is a custom server. It uses the same message-format used in the language
    server but with custom messages (i.e.: this is not the language server, but
    an API to use the bits we need from robotframework in a separate process).
    """

    def __init__(self, read_from, write_to, libspec_manager=None):
        from robotframework_ls.impl.libspec_manager import LibspecManager

        if libspec_manager is None:
            libspec_manager = LibspecManager()

        self.libspec_manager = libspec_manager
        PythonLanguageServer.__init__(self, read_from, write_to, max_workers=1)
        self._version = None

    def m_version(self):
        if self._version is not None:
            return self._version
        try:
            import robot  # @UnusedImport
        except:
            log.exception("Unable to import 'robot'.")
            version = "NO_ROBOT"
        else:
            try:
                from robot import get_version

                version = get_version(naked=True)
            except:
                log.exception("Unable to get version.")
                version = "N/A"  # Too old?
        self._version = version
        return self._version

    def _check_min_version(self, min_version):
        from robotframework_ls._utils import check_min_version

        version = self.m_version()
        return check_min_version(version, min_version)

    @overrides(PythonLanguageServer.lint)
    def lint(self, *args, **kwargs):
        pass  # No-op for this server.

    @overrides(PythonLanguageServer._create_workspace)
    def _create_workspace(self, root_uri, workspace_folders):
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        return RobotWorkspace(
            root_uri, workspace_folders, libspec_manager=self.libspec_manager
        )

    def m_lint(self, doc_uri):
        if not self._check_min_version((3, 2)):
            from robotframework_ls.lsp import Error

            msg = (
                "robotframework version (%s) too old for linting.\n"
                "Please install a newer version and restart the language server."
                % (self.m_version(),)
            )
            log.info(msg)
            return [Error(msg, (0, 0), (1, 0)).to_lsp_diagnostic()]

        try:

            workspace = self.workspace
            if not workspace:
                log.info("workspace still not initialized.")
                return []

            from robotframework_ls.impl.ast_utils import collect_errors

            document = workspace.get_document(doc_uri, create=False)
            if document is None:
                return []

            ast = document.get_ast()
            errors = collect_errors(ast)
            return [error.to_lsp_diagnostic() for error in errors]
        except:
            log.exception("Error collecting errors.")
            return []

    def m_section_name_complete(self, doc_uri, line, col):
        from robotframework_ls.impl import section_name_completions

        completion_context = self._create_completion_context(doc_uri, line, col)
        if completion_context is None:
            return []

        return section_name_completions.complete(completion_context)

    def m_keyword_complete(self, doc_uri, line, col):
        from robotframework_ls.impl import keyword_completions

        completion_context = self._create_completion_context(doc_uri, line, col)
        if completion_context is None:
            return []
        return keyword_completions.complete(completion_context)

    def m_code_format(self, text_document, options):
        from robotframework_ls.impl.formatting import robot_source_format
        from robotframework_ls.impl.formatting import create_text_edit_from_diff
        from robotframework_ls.lsp import TextDocumentItem

        text_document_item = TextDocumentItem(**text_document)
        text = text_document_item.text
        if not text:
            completion_context = self._create_completion_context(
                text_document_item.uri, 0, 0
            )
            if completion_context is None:
                return []
            text = completion_context.doc.source

        if not text:
            return []

        if options is None:
            options = {}
        tab_size = options.get("tabSize", 4)

        new_contents = robot_source_format(text, space_count=tab_size)
        if new_contents is None or new_contents == text:
            return []
        return [x.to_dict() for x in create_text_edit_from_diff(text, new_contents)]

    def _create_completion_context(self, doc_uri, line, col):
        from robotframework_ls.impl.completion_context import CompletionContext

        if not self._check_min_version((3, 2)):
            log.info("robotframework version too old for completions.")
            return None
        workspace = self.workspace
        if not workspace:
            log.info("workspace still not initialized.")
            return None

        document = workspace.get_document(doc_uri, create=False)
        if document is None:
            return None
        return CompletionContext(
            document, line, col, workspace=workspace, config=self.config
        )

    def m_shutdown(self, **_kwargs):
        ret = PythonLanguageServer.m_shutdown(self, **_kwargs)
        self.libspec_manager.dispose()
        return ret

    def m_exit(self, **_kwargs):
        ret = PythonLanguageServer.m_exit(self, **_kwargs)
        self.libspec_manager.dispose()
        return ret
