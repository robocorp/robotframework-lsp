import os
import sys
from collections import namedtuple
from robotframework_ls.constants import NULL
from robotframework_ls.robotframework_log import get_logger

log = get_logger(__name__)

_LibInfo = namedtuple("_LibInfo", "library_doc, mtime")


def _norm_filename(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


class _FolderInfo(object):
    def __init__(self, folder_path, recursive):
        self.folder_path = folder_path
        self.recursive = recursive
        self.libspec_filename_to_info = {}
        self._watch = NULL

    def start_watch(self, observer, notifier):
        if self._watch is NULL:
            if not os.path.isdir(self.folder_path):
                if not os.path.exists(self.folder_path):
                    log.info(
                        "Trying to track changes in path which does not exist: %s",
                        self.folder_path,
                    )
                else:
                    log.info(
                        "Trying to track changes in path which is not a folder: %s",
                        self.folder_path,
                    )
                return

            log.info("Tracking folder for changes: %s", self.folder_path)
            from robotframework_ls.watchdog_wrapper import PathInfo

            self._watch = observer.notify_on_extensions_change(
                [PathInfo(self.folder_path, recursive=self.recursive)],
                ["libspec"],
                notifier.on_change,
                (self._on_change_spec,),
            )

    def _on_change_spec(self, spec_file):
        spec_file = _norm_filename(spec_file)
        # Just add/remove that specific spec file from the tracked list.
        libspec_filename_to_info = self.libspec_filename_to_info.copy()
        if os.path.exists(spec_file):
            libspec_filename_to_info[spec_file] = None
        else:
            libspec_filename_to_info.pop(spec_file, None)

        self.libspec_filename_to_info = libspec_filename_to_info

    def synchronize(self):
        try:
            self.libspec_filename_to_info = self._collect_libspec_info(
                [self.folder_path],
                self.libspec_filename_to_info,
                recursive=self.recursive,
            )
        except Exception:
            log.exception("Error when synchronizing: %s", self.folder_path)

    def dispose(self):
        watch = self._watch
        self._watch = NULL
        watch.stop_tracking()
        self.libspec_filename_to_info = {}

    def _collect_libspec_info(self, folders, old_libspec_filename_to_info, recursive):
        seen_libspec_files = set()
        if recursive:
            for folder in folders:
                if os.path.isdir(folder):
                    for root, _dirs, files in os.walk(folder):
                        for filename in files:
                            if filename.lower().endswith(".libspec"):
                                seen_libspec_files.add(os.path.join(root, filename))
        else:
            for folder in folders:
                if os.path.isdir(folder):
                    for filename in os.listdir(folder):
                        if filename.lower().endswith(".libspec"):
                            seen_libspec_files.add(os.path.join(folder, filename))

        new_libspec_filename_to_info = {}

        for filename in seen_libspec_files:
            filename = _norm_filename(filename)
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
        return new_libspec_filename_to_info


class LibspecManager(object):
    """
    Used to manage the libspec files.
    
    .libspec files are searched in the following directories:

    - PYTHONPATH folders                              (not recursive)
    - Workspace folders                               (recursive -- notifications from the LSP)
    - ${user}robotframework_ls/lispec/${python_hash}  (not recursive)

    It searches for .libspec files in the folders tracked and provides the
    keywords that are available from those (properly caching data as needed).
    """

    @classmethod
    def get_internal_libspec_dir(cls):
        user_home = os.getenv("ROBOTFRAMEWORK_LS_USER_HOME", None)
        if user_home is None:
            user_home = os.path.expanduser("~")

        pyexe = sys.executable
        if not isinstance(pyexe, bytes):
            pyexe = pyexe.encode("utf-8")

        import hashlib

        digest = hashlib.sha256(pyexe).hexdigest()[:8]

        try:
            import robot

            v = str(robot.get_version())
        except:
            v = "unknown"

        return os.path.join(
            user_home, "robotframework_ls", "libspec", "%s_%s" % (digest, v)
        )

    @classmethod
    def get_internal_builtins_libspec_dir(cls, internal_libspec_dir=None):
        return os.path.join(
            internal_libspec_dir or cls.get_internal_libspec_dir(), "builtins"
        )

    def __init__(self, builtin_libspec_dir=None, user_libspec_dir=None):
        """
        :param __internal_libspec_dir__:
            Only to be used in tests (to regenerate the builtins)!
        """
        from robotframework_ls import watchdog_wrapper

        try:
            from concurrent import futures
        except ImportError:
            from robotframework_ls.libs_py2.concurrent import futures

        from multiprocessing import cpu_count

        self._thread_pool = futures.ThreadPoolExecutor(
            max_workers=(cpu_count() * 1.2) + 1
        )

        self._observer = watchdog_wrapper.create_observer()

        self._spec_changes_notifier = watchdog_wrapper.create_notifier(
            self._on_spec_file_changed, timeout=0.5
        )

        self._libspec_dir = self.get_internal_libspec_dir()

        self._user_libspec_dir = user_libspec_dir or os.path.join(
            self._libspec_dir, "user"
        )
        self._builtins_libspec_dir = (
            builtin_libspec_dir
            or self.get_internal_builtins_libspec_dir(self._libspec_dir)
        )
        log.debug("User libspec dir: %s", self._user_libspec_dir)
        log.debug("Builtins libspec dir: %s", self._builtins_libspec_dir)

        try:
            os.makedirs(self._user_libspec_dir)
        except:
            # Ignore exception if it's already created.
            pass
        try:
            os.makedirs(self._builtins_libspec_dir)
        except:
            # Ignore exception if it's already created.
            pass

        # Spec info found in the workspace
        self._workspace_folder_uri_to_folder_info = {}

        # Spec info found in the pythonpath
        pythonpath_folder_to_folder_info = {}
        for path in sys.path:
            if path and os.path.isdir(path):
                pythonpath_folder_to_folder_info[path] = _FolderInfo(
                    path, recursive=False
                )
        self._pythonpath_folder_to_folder_info = pythonpath_folder_to_folder_info

        # Spec info found in internal dirs (autogenerated)
        self._internal_folder_to_folder_info = {
            self._user_libspec_dir: _FolderInfo(
                self._user_libspec_dir, recursive=False
            ),
            self._builtins_libspec_dir: _FolderInfo(
                self._builtins_libspec_dir, recursive=False
            ),
        }

        self._synchronize()
        self._gen_builtin_libraries()

    @property
    def user_libspec_dir(self):
        return self._user_libspec_dir

    def _on_spec_file_changed(self, spec_file, target):
        log.debug("File change detected: %s", spec_file)
        target(spec_file)

    def add_workspace_folder(self, folder_uri):
        from robotframework_ls import uris

        if folder_uri not in self._workspace_folder_uri_to_folder_info:
            log.debug("Added workspace folder: %s", folder_uri)
            cp = self._workspace_folder_uri_to_folder_info.copy()
            folder_info = cp[folder_uri] = _FolderInfo(
                uris.to_fs_path(folder_uri), recursive=True
            )
            self._workspace_folder_uri_to_folder_info = cp
            folder_info.start_watch(self._observer, self._spec_changes_notifier)
            folder_info.synchronize()
        else:
            log.debug("Workspace folder already added: %s", folder_uri)

    def remove_workspace_folder(self, folder_uri):
        if folder_uri in self._workspace_folder_uri_to_folder_info:
            log.debug("Removed workspace folder: %s", folder_uri)
            cp = self._workspace_folder_uri_to_folder_info.copy()
            folder_info = cp.pop(folder_uri, NULL)
            folder_info.dispose()
            self._workspace_folder_uri_to_folder_info = cp
        else:
            log.debug("Workspace folder already removed: %s", folder_uri)

    def _gen_builtin_libraries(self):
        """
        Generates .lispec files for the libraries builtin (if needed).
        """
        import time

        try:
            from robotframework_ls.impl import robot_constants

            initial_time = time.time()

            wait_for = []
            for libname in robot_constants.STDLIBS:
                library_info = self.get_library_info(libname, create=False)
                if library_info is None:
                    wait_for.append(
                        self._thread_pool.submit(
                            self._create_libspec, libname, retry=False
                        )
                    )
            for future in wait_for:
                future.result()

            if wait_for:
                log.debug(
                    "Total time to generate builtins: %.2fs"
                    % (time.time() - initial_time)
                )
                self.synchronize_internal_libspec_folders()
        except:
            log.exception("Error creating builtin libraries.")

    def synchronize_workspace_folders(self):
        for _uri, folder_info in self._workspace_folder_uri_to_folder_info.items():
            folder_info.start_watch(self._observer, self._spec_changes_notifier)
            folder_info.synchronize()

    def synchronize_pythonpath_folders(self):
        for _folder_path, folder_info in self._pythonpath_folder_to_folder_info.items():
            folder_info.start_watch(self._observer, self._spec_changes_notifier)
            folder_info.synchronize()

    def synchronize_internal_libspec_folders(self):
        for _folder_path, folder_info in self._internal_folder_to_folder_info.items():
            folder_info.start_watch(self._observer, self._spec_changes_notifier)
            folder_info.synchronize()

    def _synchronize(self):
        """
        Updates the internal caches related to the tracked .libspec files found.
        
        This can be a slow call as it may traverse the whole workspace folders
        hierarchy, so, it should be used only during startup to fill the initial
        info.
        """
        self.synchronize_workspace_folders()
        self.synchronize_pythonpath_folders()
        self.synchronize_internal_libspec_folders()

    def _iter_library_doc(self):
        """
        :rtype: generator(LibraryDoc)
        """
        found_libraries = set()

        # Note: the iteration order is important (first ones are visited earlier
        # and have higher priority).
        iter_in = []
        for (_uri, info) in self._workspace_folder_uri_to_folder_info.items():
            iter_in.append(info.libspec_filename_to_info)

        for (_uri, info) in self._pythonpath_folder_to_folder_info.items():
            iter_in.append(info.libspec_filename_to_info)

        for (_uri, info) in self._internal_folder_to_folder_info.items():
            iter_in.append(info.libspec_filename_to_info)

        for filename_to_info in iter_in:
            for filename, info in list(filename_to_info.items()):
                if info is not None:
                    try:
                        if info.mtime != os.path.getmtime(filename):
                            info = None
                    except:
                        continue
                if info is None:
                    info = filename_to_info[filename] = self._load_info(filename)

                if info is not None and info.library_doc is not None:
                    if info.library_doc.name not in found_libraries:
                        found_libraries.add(info.library_doc.name)
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

    def _create_libspec(
        self,
        libname,
        env=None,
        retry=True,
        log_time=True,
        cwd=None,
        additional_path=None,
    ):
        """
        :param str libname:
        :raise Exception: if unable to create the library.
        """
        from robotframework_ls import uris
        import time
        from robotframework_ls.impl import robot_constants
        from robotframework_ls.subprocess_wrapper import subprocess
        from robotframework_ls.constants import IS_PY2

        curtime = time.time()

        try:
            call = [sys.executable]
            call.extend("-m robot.libdoc --format XML:HTML".split())
            if additional_path:
                call.extend(["-P", additional_path])

            call.append(libname)
            libspec_dir = self._user_libspec_dir
            if libname in robot_constants.STDLIBS:
                libspec_dir = self._builtins_libspec_dir

            target = os.path.join(libspec_dir, libname + ".libspec")
            call.append(target)

            mtime = -1
            try:
                mtime = os.path.getmtime(target)
            except:
                pass

            log.debug(
                "Generating libspec for: %s.\nCommand line:\n%s",
                libname,
                " ".join(call),
            )
            try:
                try:
                    # Note: stdout is always subprocess.PIPE in this call.
                    subprocess.check_output(
                        call,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.PIPE,
                        env=env,
                        cwd=cwd,
                    )
                except OSError as e:
                    log.exception("Error calling: %s", call)
                    # We may have something as: Ignore OSError: [WinError 6] The handle is invalid,
                    # give the result based on whether the file changed on disk.
                    try:
                        if mtime != os.path.getmtime(target):
                            return True
                    except:
                        pass

                    if not retry:
                        log.debug("Not retrying after OSError failure.")
                        return False

                    log.debug("Retrying after OSError failure.")
                    raise subprocess.CalledProcessError(1, call, b"ImportError")

            except subprocess.CalledProcessError as e:
                if b"ImportError" in e.output or b"ModuleNotFoundError" in e.output:
                    if retry:
                        as_path = libname.replace(".", "/")
                        as_path += ".py"
                        for folder_uri in self._workspace_folder_uri_to_folder_info:
                            folder = uris.to_fs_path(folder_uri)
                            if os.path.exists(os.path.join(folder, as_path)):
                                # Let's see if we can find the module in the workspace (if we
                                # can, fix the PYTHONPATH to include it).
                                env_cp = os.environ.copy()
                                if IS_PY2:
                                    if not isinstance(folder, bytes):
                                        folder = folder.encode(
                                            sys.getfilesystemencoding()
                                        )
                                env_cp["PYTHONPATH"] = (
                                    folder
                                    + os.pathsep
                                    + os.environ.get("PYTHONPATH", "")
                                )
                                return self._create_libspec(
                                    libname,
                                    env=env_cp,
                                    retry=False,
                                    log_time=False,
                                    cwd=cwd,
                                    additional_path=additional_path,
                                )

                log.exception(
                    "Error creating libspec: %s. Output:\n%s", libname, e.output
                )
                return False
            return True
        finally:
            if log_time:
                delta = time.time() - curtime
                log.debug("Took: %.2fs to generate info for: %s" % (delta, libname))

    def dispose(self):
        self._observer.dispose()
        self._spec_changes_notifier.dispose()

    def get_library_info(self, libname, create=True, current_doc_uri=None):
        """
        :param libname:
            It may be a library name, a relative path to a .py file or an
            absolute path to a .py file.

        :rtype: LibraryDoc
        """
        from robotframework_ls import uris

        libname_lower = libname.lower()
        if libname_lower.endswith((".py", ".class", ".java")):
            libname_lower = os.path.splitext(libname)[0]

        if "/" in libname_lower or "\\" in libname_lower:
            libname_lower = os.path.basename(libname_lower)

        for library_doc in self._iter_library_doc():
            if library_doc.name and library_doc.name.lower() == libname_lower:
                return library_doc

        if create:
            additional_path = None
            abspath = None
            cwd = None
            if current_doc_uri is not None:
                cwd = os.path.dirname(uris.to_fs_path(current_doc_uri))

            if os.path.isabs(libname):
                abspath = libname

            elif current_doc_uri is not None:
                # relative path: let's make it absolute
                fs_path = os.path.dirname(uris.to_fs_path(current_doc_uri))
                abspath = os.path.abspath(os.path.join(fs_path, libname))

            if abspath:
                additional_path = os.path.dirname(abspath)
                libname = os.path.basename(libname)
                if libname.lower().endswith((".py", ".class", ".java")):
                    libname = os.path.splitext(libname)[0]

            if self._create_libspec(libname, additional_path=additional_path, cwd=cwd):
                self.synchronize_internal_libspec_folders()
                return self.get_library_info(
                    libname, create=False, current_doc_uri=current_doc_uri
                )

        log.debug("Unable to find library named: %s", libname)
        return None
