import os
import subprocess
import sys
import logging
from collections import namedtuple

log = logging.getLogger(__name__)

_LibInfo = namedtuple("_LibInfo", "library_doc, mtime")


class LibspecManager(object):
    """
    Used to manage the libspec files.
    
    .libspec files are searched in the following directories:

    - PYTHONPATH folders               (not recursive)
    - Workspace folders                (recursive -- notifications from the LSP)
    - ${user}robotframework_ls/lispec/ (not recursive)

    It searches for .libspec files in the folders tracked and provides the
    keywords that are available from those (properly caching data as needed).
    """

    def __init__(self, user_home=None):
        self._workspace_folders_tracked = set()
        self._libspec_filename_to_info = {}
        if user_home is None:
            user_home = os.path.expanduser("~")

        self._user_home = user_home

        pyexe = sys.executable
        if not isinstance(pyexe, bytes):
            pyexe = pyexe.encode("utf-8")

        import hashlib

        digest = hashlib.sha256(pyexe).hexdigest()[:8]

        self._libspec_dir = os.path.join(
            user_home, "robotframework_ls", "libspec", digest
        )

        try:
            os.makedirs(self._libspec_dir)
        except:
            # Ignore exception if it's already created.
            pass

    @property
    def libspec_dir(self):
        return self._libspec_dir

    def add_workspace_folder(self, folder_uri):
        if folder_uri not in self._workspace_folders_tracked:
            self._workspace_folders_tracked.add(folder_uri)

    def remove_workspace_folder(self, folder_uri):
        if folder_uri in self._workspace_folders_tracked:
            self._workspace_folders_tracked.discard(folder_uri)

    def synchronize(self):
        from robotframework_ls import uris

        seen_libspec_files = set()
        for folder in self._workspace_folders_tracked.copy():
            folder = uris.to_fs_path(folder)
            for root, _dirs, files in os.walk(folder):
                for filename in files:
                    if filename.lower().endswith(".libspec"):
                        seen_libspec_files.add(os.path.join(root, filename))

        for filename in os.listdir(self._libspec_dir):
            if filename.lower().endswith(".libspec"):
                seen_libspec_files.add(os.path.join(self._libspec_dir, filename))

        old_libspec_filename_to_info = self._libspec_filename_to_info
        new_libspec_filename_to_info = {}

        for filename in seen_libspec_files:
            info = old_libspec_filename_to_info.get(filename)
            if info is not None:
                try:
                    curr_mtime = os.path.getmtime(filename)
                except:
                    # it was deleted in the meanwhile...
                    continue
                else:
                    if info.mtime != curr_mtime:
                        info = None

            new_libspec_filename_to_info[filename] = info
        self._libspec_filename_to_info = new_libspec_filename_to_info

    def _iter_library_doc(self):
        filename_to_info = self._libspec_filename_to_info
        for filename, info in list(filename_to_info.items()):
            if info is not None:
                try:
                    if info.mtime != os.path.getmtime(filename):
                        info = None
                except:
                    continue
            if info is None:
                info = filename_to_info[filename] = self._load_info(filename)
            if info is not None:
                yield info.library_doc

    def _load_info(self, filename):
        from robotframework_ls.impl import robot_specbuilder

        builder = robot_specbuilder.SpecDocBuilder()
        try:
            mtime = os.path.getmtime(filename)
            libdoc = builder.build(filename)
            return _LibInfo(libdoc, mtime)
        except Exception:
            log.exception("Error when loading spec info from: %s", filename)
            return None

    def get_library_names(self):
        return [library_doc.name for library_doc in self._iter_library_doc()]

    def create_libspec(self, libname, env=None, retry=True):
        """
        :param str libname:
        :raise Exception: if unable to create the library.
        """
        from robotframework_ls import uris

        call = [sys.executable]
        call.extend("-m robot.libdoc --format xml".split())
        call.append(libname)
        call.append(os.path.join(self._libspec_dir, libname + ".libspec"))
        try:
            subprocess.check_output(call, stderr=subprocess.STDOUT, env=env)
        except subprocess.CalledProcessError as e:
            if b"ImportError" in e.output or b"ModuleNotFoundError" in e.output:
                if retry:
                    as_path = libname.replace(".", "/")
                    as_path += ".py"
                    for folder in self._workspace_folders_tracked:
                        folder = uris.to_fs_path(folder)
                        if os.path.exists(os.path.join(folder, as_path)):
                            # Let's see if we can find the module in the workspace (if we
                            # can, fix the PYTHONPATH to include it).
                            env_cp = os.environ.copy()
                            env_cp["PYTHONPATH"] = (
                                folder + os.pathsep + os.environ.get("PYTHONPATH", "")
                            )
                            return self.create_libspec(libname, env=env_cp, retry=False)

            log.exception("Error creating libspec: %s. Output:\n%s", libname, e.output)
            return False
        return True

    def dispose(self):
        pass

    def get_library_info(self, libname, create=True):
        for library_doc in self._iter_library_doc():
            if library_doc.name == libname:
                return library_doc

        if create:
            if self.create_libspec(libname):
                self.synchronize()
                return self.get_library_info(libname, create=False)
        raise KeyError("Unable to find library named: %s" % (libname,))
