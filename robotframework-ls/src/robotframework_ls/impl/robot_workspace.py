from robocorp_ls_core.workspace import Workspace, Document
from robocorp_ls_core.basic import overrides
from robocorp_ls_core.cache import instance_cache
from robotframework_ls.constants import NULL
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import IRobotWorkspace, IRobotDocument
from robocorp_ls_core.protocols import check_implements, IWorkspaceFolder
from robocorp_ls_core.watchdog_wrapper import IFSObserver
from typing import Optional, Any

log = get_logger(__name__)


class RobotWorkspace(Workspace):
    def __init__(
        self,
        root_uri,
        fs_observer: IFSObserver,
        workspace_folders=None,
        libspec_manager=NULL,
        generate_ast=True,
    ):
        self.libspec_manager = libspec_manager

        Workspace.__init__(
            self, root_uri, fs_observer, workspace_folders=workspace_folders
        )
        self._generate_ast = generate_ast

    @overrides(Workspace.add_folder)
    def add_folder(self, folder: IWorkspaceFolder):
        Workspace.add_folder(self, folder)
        self.libspec_manager.add_workspace_folder(folder.uri)

    @overrides(Workspace.remove_folder)
    def remove_folder(self, folder_uri):
        Workspace.remove_folder(self, folder_uri)
        self.libspec_manager.remove_workspace_folder(folder_uri)

    def _create_document(self, doc_uri, source=None, version=None):
        return RobotDocument(doc_uri, source, version, generate_ast=self._generate_ast)

    def __typecheckself__(self) -> None:
        _: IRobotWorkspace = check_implements(self)


class RobotDocument(Document):

    TYPE_TEST_CASE = "test_case"
    TYPE_INIT = "init"
    TYPE_RESOURCE = "resource"

    def __init__(self, uri, source=None, version=None, generate_ast=True):
        Document.__init__(self, uri, source=source, version=version)

        self._generate_ast = generate_ast
        self._ast = None
        self.symbols_cache = None

    @overrides(Document._clear_caches)
    def _clear_caches(self):
        Document._clear_caches(self)
        self._symbols_cache = None
        self.get_ast.cache_clear(self)  # noqa (clear the instance_cache).
        self.get_python_ast.cache_clear(self)  # noqa (clear the instance_cache).
        self.get_yaml_contents.cache_clear(self)  # noqa (clear the instance_cache).

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
        from robot.api import get_model, get_resource_model, get_init_model  # noqa

        try:
            source = self.source
        except:
            log.exception("Error getting source for: %s" % (self.uri,))
            source = ""

        try:
            t = self.get_type()
            if t == self.TYPE_TEST_CASE:
                ast = get_model(source)

            elif t == self.TYPE_RESOURCE:
                ast = get_resource_model(source)

            elif t == self.TYPE_INIT:
                ast = get_init_model(source)

            else:
                log.critical("Unrecognized section: %s", t)
                ast = get_model(source)

            ast.source = self.path
            return ast
        except:
            log.critical(f"Error parsing {self.uri}")
            # Note: we always want to return a valid AST here (the
            # AST itself should have the error).
            ast = get_model(f"*** Unable to parse: {self.uri} ***")
            ast.source = self.path
            return ast

    @instance_cache
    def get_python_ast(self):
        if not self._generate_ast:
            raise AssertionError(
                "The AST can only be accessed in the RobotFrameworkServerApi, not in the RobotFrameworkLanguageServer."
            )

        try:
            source = self.source
        except:
            log.exception("Error getting source for: %s" % (self.uri,))
            return None

        try:
            import ast as ast_module

            return ast_module.parse(source)
        except:
            log.critical(f"Error parsing python file: {self.uri}")
            return None

    @instance_cache
    def get_yaml_contents(self) -> Optional[Any]:
        try:
            source = self.source
        except:
            log.exception("Error getting source for: %s" % (self.uri,))
            return None

        try:
            from robocorp_ls_core import yaml_wrapper
            from io import StringIO

            s = StringIO()
            s.write(source)
            s.seek(0)
            return yaml_wrapper.load(s)
        except:
            log.critical(f"Error parsing yaml file: {self.uri}")
            return None

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

    def __typecheckself__(self) -> None:
        _: IRobotDocument = check_implements(self)
