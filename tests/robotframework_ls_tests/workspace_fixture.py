import os.path

__file__ = os.path.abspath(__file__)


class WorkspaceFixture(object):
    def __init__(self):
        self.resources_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "resources"
        )
        assert os.path.exists(self.resources_dir)
        self._ws = None

    @property
    def ws(self):
        if self._ws is None:
            raise AssertionError(
                "set_root must be called prior to using the workspace."
            )
        return self._ws

    def set_root(self, relative_path, **kwargs):
        from robotframework_ls import uris
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        path = self._get_path_relative_to_resources(relative_path)
        self._ws = RobotWorkspace(uris.from_fs_path(path), **kwargs)

    def _get_path_relative_to_resources(self, resources_relative_path, must_exist=True):
        path = os.path.join(self.resources_dir, resources_relative_path)
        if must_exist:
            assert os.path.exists(path), "%s does not exist." % (path,)
        return path

    def get_doc(self, root_relative_path, create=True):
        from robotframework_ls import uris

        path = os.path.join(self._ws.root_path, root_relative_path)
        uri = uris.from_fs_path(path)
        return self.ws.get_document(uri, create=create)
