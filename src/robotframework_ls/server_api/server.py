from robotframework_ls.python_ls import PythonLanguageServer
import logging


log = logging.getLogger(__name__)


class RobotFrameworkServerApi(PythonLanguageServer):
    """
    This is a custom server. It uses the same message-format used in the language
    server but with custom messages (i.e.: this is not the language server, but
    an API to use the bits we need from robotframework in a separate process).
    """

    def __init__(self, read_from, write_to):
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

    def lint(self, *args, **kwargs):
        pass  # No-op for this server.

    def _create_workspace(self, root_uri, workspace_folders):
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        return RobotWorkspace(root_uri, workspace_folders)

    def m_lint(self, doc_uri):
        if not self._check_min_version((3, 2)):
            from robotframework_ls.server_api.errors import Error

            msg = (
                "robotframework version (%s) too old for linting.\n"
                "Please install a newer version and restart the language server."
                % (self.m_version(),)
            )
            log.info(msg)
            return [Error(msg, (0, 0), (1, 0)).to_lsp_diagnostic()]

        try:
            from robotframework_ls.server_api.errors import collect_errors

            document = self.workspace.get_document(doc_uri, create=False)
            if document is None:
                return []

            source = document.source
            errors = collect_errors(source)
            return [error.to_lsp_diagnostic() for error in errors]
        except:
            log.exception("Error collecting errors.")
            return []

    def m_section_name_complete(self, doc_uri, line, col):
        from robotframework_ls.impl import section_name_completions
        from robotframework_ls.impl.completion_context import CompletionContext

        if not self._check_min_version((3, 2)):
            log.info("robotframework version too old for completions.")
            return []

        document = self.workspace.get_document(doc_uri, create=False)
        if document is None:
            return []
        return section_name_completions.complete(CompletionContext(document, line, col))
