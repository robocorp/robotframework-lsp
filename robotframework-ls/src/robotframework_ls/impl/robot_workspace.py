from robocorp_ls_core.workspace import Workspace, Document
from robocorp_ls_core.basic import overrides
from robocorp_ls_core.cache import instance_cache
from robotframework_ls.constants import NULL
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class RobotWorkspace(Workspace):
    def __init__(
        self, root_uri, workspace_folders=None, libspec_manager=NULL, generate_ast=True
    ):
        self.libspec_manager = libspec_manager

        Workspace.__init__(self, root_uri, workspace_folders=workspace_folders)
        self._generate_ast = generate_ast

    @overrides(Workspace.add_folder)
    def add_folder(self, folder):
        Workspace.add_folder(self, folder)
        self.libspec_manager.add_workspace_folder(folder.uri)

    @overrides(Workspace.remove_folder)
    def remove_folder(self, folder_uri):
        Workspace.remove_folder(self, folder_uri)
        self.libspec_manager.remove_workspace_folder(folder_uri)

    def _create_document(self, doc_uri, source=None, version=None):
        return RobotDocument(doc_uri, source, version, generate_ast=self._generate_ast)


class RobotDocument(Document):

    TYPE_TEST_CASE = "test_case"
    TYPE_INIT = "init"
    TYPE_RESOURCE = "resource"

    def __init__(self, uri, source=None, version=None, generate_ast=True):
        Document.__init__(self, uri, source=source, version=version)
        self._generate_ast = generate_ast
        self._ast = None

    @overrides(Document._clear_caches)
    def _clear_caches(self):
        Document._clear_caches(self)
        self.get_ast.cache_clear(self)

    def get_type(self):
        path = self.path
        if not path:
            log.info("RobotDocument path empty.")
            return self.TYPE_TEST_CASE

        import os.path

        basename = os.path.basename(path)
        if basename.startswith("__init__"):
            return self.TYPE_INIT

        if basename.endswith(".resource"):
            return self.TYPE_RESOURCE

        return self.TYPE_TEST_CASE

    @instance_cache
    def get_ast(self):
        if not self._generate_ast:
            raise AssertionError(
                "The AST can only be accessed in the RobotFrameworkServerApi, not in the RobotFrameworkLanguageServer."
            )
        from robot.api import get_model, get_resource_model, get_init_model

        try:
            source = self.source
        except:
            log.exception("Error getting source for: %s" % (self.uri,))
            source = ""

        t = self.get_type()
        if t == self.TYPE_TEST_CASE:
            return get_model(source)

        elif t == self.TYPE_RESOURCE:
            return get_resource_model(source)

        elif t == self.TYPE_INIT:
            return get_init_model(source)

        else:
            log.critical("Unrecognized section: %s", t)
            return get_model(source)

    def find_line_with_contents(self, contents: str) -> int:
        """
        :param contents:
            The contents to be found.
            
        :return:
            The 0-based index of the contents.
        """
        for i, line in enumerate(self.iter_lines()):
            if contents in line:
                return i
        else:
            raise AssertionError(f"Did not find >>{contents}<< in doc.")
