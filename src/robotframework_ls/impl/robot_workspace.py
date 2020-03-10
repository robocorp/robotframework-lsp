from robotframework_ls.workspace import Workspace, Document
import logging
from robotframework_ls._utils import overrides
from robotframework_ls.cache import instance_cache

log = logging.getLogger(__name__)


class RobotWorkspace(Workspace):
    def _create_document(self, doc_uri, source=None, version=None):
        return RobotDocument(doc_uri, source, version)


class RobotDocument(Document):

    TYPE_TEST_CASE = "test_case"
    TYPE_INIT = "init"
    TYPE_RESOURCE = "resource"

    def __init__(self, uri, source=None, version=None):
        Document.__init__(self, uri, source=source, version=version)
        self._ast = None

    @overrides(Document._clear_caches)
    def _clear_caches(self):
        Document._clear_caches(self)
        self.get_ast.clear_cache(self)

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
        from robotframework_ls.impl import robot_constants
        from robot.parsing import get_model, get_resource_model, get_init_model

        source = self.source

        t = self.get_type()
        if t == self.TYPE_TEST_CASE:
            return get_model(source)

        elif t == self.TYPE_RESOURCE:
            return get_resource_model(source)

        elif t == self.TYPE_INIT:
            return get_init_model(source)

        else:
            log.critical("Unrecognized section: %s", t)
            return robot_constants.TEST_CASE_FILE_SECTIONS
