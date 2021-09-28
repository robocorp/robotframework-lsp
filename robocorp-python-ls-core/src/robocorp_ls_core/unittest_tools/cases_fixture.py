import os.path


class CasesFixture(object):
    def __init__(self, copy_to_dir: str, original_resources_dir: str):
        """
        Upon initialization copies the `original_resources_dir` to
        `copy_to_dir`.

        So, for instance, we may copy the contents from

        /my/test/resource

        to

        /temp/pytest-101/folder with spaces/resource

        Subsequent requests to get the path will access it in the
        place we copied it to.

        Note: it should usually be bound to a session scope so that
        the copy isn't done at each call.
        """
        from robocorp_ls_core.copytree import copytree_dst_exists

        copytree_dst_exists(original_resources_dir, copy_to_dir)
        self.resources_dir = copy_to_dir
        assert os.path.exists(self.resources_dir)

    def get_path(self, resources_relative_path: str, must_exist=True) -> str:
        """
        Returns a path from the resources dir.
        """
        path = os.path.join(self.resources_dir, resources_relative_path)
        if must_exist:
            assert os.path.exists(path), "%s does not exist." % (path,)
        return path

    def copy_to(self, case: str, dest_dir: str):
        """
        Helper to copy a given path to a given directory.

        To be used if a given path should be within another structure or
        if its contents should be mutated.
        """
        import shutil

        src = self.get_path(case, must_exist=True)

        shutil.copytree(src, dest_dir)
