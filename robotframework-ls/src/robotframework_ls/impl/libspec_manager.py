import os
import sys
from robotframework_ls.constants import NULL
from robocorp_ls_core.robotframework_log import get_logger
import threading
from typing import Optional, Dict, Set, Iterator, Union, Any
from robocorp_ls_core.protocols import Sentinel, IEndPoint
from robotframework_ls.impl.protocols import (
    ILibraryDoc,
    ILibraryDocOrError,
    ICompletionContext,
    ILibraryDocConversions,
)
import itertools
from robocorp_ls_core.watchdog_wrapper import IFSObserver
from robotframework_ls.impl.robot_lsp_constants import (
    OPTION_ROBOT_LIBRARIES_LIBDOC_NEEDS_ARGS,
)
from robotframework_ls.impl.libspec_warmup import (
    _norm_filename,
    _normfile,
    LibspecWarmup,
)
from pathlib import Path
from contextlib import contextmanager
import typing
from robotframework_ls.impl.text_utilities import get_digest_from_string
from robocorp_ls_core.basic import normalize_filename

log = get_logger(__name__)


def _get_libspec_mutex_name(libspec_filename):
    from robocorp_ls_core.system_mutex import generate_mutex_name

    libspec_filename = _norm_filename(libspec_filename)
    basename = os.path.basename(libspec_filename)
    name = os.path.splitext(basename)[0]
    return generate_mutex_name(libspec_filename, prefix="%s_" % (name,))


def _get_additional_info_filename(spec_filename):
    additional_info_filename = os.path.join(spec_filename + ".m")
    return additional_info_filename


@contextmanager
def _timed_acquire_mutex_for_spec_filename(spec_filename):
    from robocorp_ls_core.system_mutex import timed_acquire_mutex

    try:
        ctx = timed_acquire_mutex(_get_libspec_mutex_name(spec_filename), timeout=30)
        ctx.__enter__()
    except:
        raise RuntimeError(
            f"Unable to get mutex for: {spec_filename} after 30 seconds."
        )
    try:
        yield ctx
    finally:
        ctx.__exit__()


def _load_library_doc_and_mtime(libspec_manager, spec_filename: str, obtain_mutex=True):
    """
    :param obtain_mutex:
        Should be False if this is part of a bigger operation that already
        has the spec_filename mutex.
    """
    from robotframework_ls.impl import robot_specbuilder
    from robotframework_ls.impl.libspec_markdown_conversion import (
        load_markdown_json_version,
    )

    ctx: Any
    if obtain_mutex:
        ctx = _timed_acquire_mutex_for_spec_filename(spec_filename)
    else:
        ctx = NULL
    with ctx:
        # We must load it with a mutex to avoid conflicts between generating/reading.
        try:
            mtime = os.path.getmtime(spec_filename)
            if not libspec_manager.is_copy:
                libdoc = load_markdown_json_version(
                    libspec_manager, spec_filename, mtime
                )

                if libdoc is None:
                    builder = robot_specbuilder.SpecDocBuilder()
                    libdoc = builder.build(spec_filename)
                    if libdoc.doc_format != "markdown":
                        libspec_manager.schedule_conversion_to_markdown(spec_filename)
                return libdoc, mtime

            else:
                # For a copy we don't use markdown by default, rather
                # we always use the raw format and convert as needed.
                builder = robot_specbuilder.SpecDocBuilder()
                libdoc = builder.build(spec_filename)
                return libdoc, mtime
        except Exception:
            log.exception("Error when loading spec info from: %s", spec_filename)
            return None


def _load_lib_info(libspec_manager, canonical_spec_filename: str, can_regenerate: bool):
    libdoc_and_mtime = _load_library_doc_and_mtime(
        libspec_manager, canonical_spec_filename
    )
    if libdoc_and_mtime is None:
        return None
    libdoc, mtime = libdoc_and_mtime
    return _LibInfo(libdoc, mtime, canonical_spec_filename, can_regenerate)


_IS_BUILTIN = "is_builtin"
_SOURCE_TO_MTIME = "source_to_mtime"
_UNABLE_TO_LOAD = "unable_to_load"


def _create_updated_source_to_mtime(library_doc):
    sources = set()

    source = library_doc.source
    if source is not None:
        sources.add(source)

    for keyword in library_doc.keywords:
        source = keyword.source
        if source is not None:
            sources.add(source)

    source_to_mtime = {}
    for source in sources:
        try:
            # i.e.: get it before normalizing (but leave the cache key normalized).
            # This is because even on windows the file-system may end up being
            # case-dependent on some cases.
            mtime = os.path.getmtime(source)
            source = _normfile(source)
            source_to_mtime[source] = mtime
        except Exception:
            log.exception("Unable to load source for file: %s", source)
    return source_to_mtime


def _create_additional_info(
    libspec_manager, spec_filename, is_builtin, obtain_mutex=True
):
    try:
        additional_info = {_IS_BUILTIN: is_builtin}
        if is_builtin:
            # For builtins we don't have to check the mtime
            # (on a new version we update the folder).
            return additional_info

        library_doc_and_mtime = _load_library_doc_and_mtime(
            libspec_manager, spec_filename, obtain_mutex=obtain_mutex
        )
        if library_doc_and_mtime is None:
            additional_info[_UNABLE_TO_LOAD] = True
            return additional_info

        library_doc = library_doc_and_mtime[0]

        additional_info[_SOURCE_TO_MTIME] = _create_updated_source_to_mtime(library_doc)
        return additional_info

    except:
        log.exception(
            "Error creating additional info for spec filename: %s", spec_filename
        )
        return {}


def _load_spec_filename_additional_info(spec_filename):
    """
    Loads additional information given a spec filename.
    """
    import json

    try:
        additional_info_filename = _get_additional_info_filename(spec_filename)

        with open(additional_info_filename, "r") as stream:
            source_to_mtime = json.load(stream)
        return source_to_mtime
    except:
        log.exception("Unable to load source mtimes from: %s", additional_info_filename)
        return {}


def _dump_spec_filename_additional_info(
    libspec_manager, spec_filename, is_builtin, obtain_mutex=True
):
    """
    Creates a filename with additional information not directly available in the
    spec.
    """
    try:
        if not libspec_manager.is_copy:
            libspec_manager.schedule_conversion_to_markdown(spec_filename)
    except:
        log.exception("Error converting %s to markdown.", spec_filename)
    import json

    source_to_mtime = _create_additional_info(
        libspec_manager, spec_filename, is_builtin, obtain_mutex=obtain_mutex
    )
    additional_info_filename = _get_additional_info_filename(spec_filename)
    with open(additional_info_filename, "w") as stream:
        json.dump(source_to_mtime, stream, indent=2, sort_keys=True)


class _LibInfo(object):
    __slots__ = [
        "library_doc",
        "mtime",
        "_canonical_spec_filename",
        "_additional_info",
        "_invalid",
        "_can_regenerate",
    ]

    def __init__(self, library_doc: ILibraryDoc, mtime, spec_filename, can_regenerate):
        """
        :param library_doc:
        :param mtime:
        :param spec_filename:
        :param bool can_regenerate:
            False means that the information from this file can't really be
            regenerated (i.e.: this is a spec file from a library or created
            by the user).
        """
        assert library_doc
        assert mtime
        assert spec_filename

        self.library_doc = library_doc
        self.mtime = mtime

        self._can_regenerate = can_regenerate
        self._canonical_spec_filename = spec_filename
        self._additional_info = None
        self._invalid = False

    def __str__(self):
        return f"_LibInfo({self.library_doc}, {self.mtime})"

    def verify_sources_sync(self):
        """
        :return bool:
            True if everything is ok and this library info can be used. Otherwise,
            the spec file and the _LibInfo must be recreated.
        """
        if not self._can_regenerate:
            # This means that this info was generated by a library or the user
            # himself, thus, we can't regenerate it.
            return True

        if self._invalid:  # Once invalid, always invalid.
            return False

        additional_info = self._additional_info
        if additional_info is None:
            additional_info = _load_spec_filename_additional_info(
                self._canonical_spec_filename
            )
            if additional_info.get(_IS_BUILTIN, False):
                return True

            source_to_mtime = additional_info.get(_SOURCE_TO_MTIME)
            if source_to_mtime is None:
                # Nothing to validate...
                return True

            updated_source_to_mtime = _create_updated_source_to_mtime(self.library_doc)
            if source_to_mtime != updated_source_to_mtime:
                log.info(
                    "Library %s is invalid. Current source to mtime:\n%s\nChanged from:\n%s"
                    % (self.library_doc.name, source_to_mtime, updated_source_to_mtime)
                )
                self._invalid = True
                return False

        return True


class _FolderInfo(object):
    def __init__(self, folder_path, recursive):
        self.folder_path = folder_path
        self.recursive = recursive
        self.libspec_canonical_filename_to_info = {}
        self._watch = NULL
        self._lock = threading.Lock()

    def start_watch(self, observer, notifier):
        with self._lock:
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

                log.debug("Tracking folder for changes: %s", self.folder_path)
                from robocorp_ls_core.watchdog_wrapper import PathInfo

                folder_path = self.folder_path
                self._watch = observer.notify_on_any_change(
                    [PathInfo(folder_path, recursive=self.recursive)],
                    notifier.on_change,
                    (self._on_change_spec,),
                    extensions=(".py", ".libspec"),
                )

    def _on_change_spec(self, spec_file):
        with self._lock:
            spec_file_key = _norm_filename(spec_file)
            # Just add/remove that specific spec file from the tracked list.
            libspec_canonical_filename_to_info = (
                self.libspec_canonical_filename_to_info.copy()
            )
            if os.path.exists(spec_file):
                libspec_canonical_filename_to_info[spec_file_key] = None
            else:
                libspec_canonical_filename_to_info.pop(spec_file_key, None)

            self.libspec_canonical_filename_to_info = libspec_canonical_filename_to_info

    def synchronize(self):
        with self._lock:
            try:
                self.libspec_canonical_filename_to_info = self._collect_libspec_info(
                    [self.folder_path],
                    self.libspec_canonical_filename_to_info,
                    recursive=self.recursive,
                )
            except Exception:
                log.exception("Error when synchronizing: %s", self.folder_path)

    def dispose(self):
        with self._lock:
            watch = self._watch
            self._watch = NULL
            watch.stop_tracking()
            self.libspec_canonical_filename_to_info = {}

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

        new_libspec_filename_to_info: Dict[str, _LibInfo] = {}

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
                        # The spec filename mtime changed, so, set to None
                        # to reload it.
                        info = None

            new_libspec_filename_to_info[filename] = info
        return new_libspec_filename_to_info


class LibspecManager(object):
    """
    Used to manage the libspec files.

    .libspec files are searched in the following directories:

    - PYTHONPATH folders                                  (not recursive)
    - Workspace folders                                   (recursive -- notifications from the LSP)
    - ${user}.robotframework-ls/specs/${python_hash}      (not recursive)

    It searches for .libspec files in the folders tracked and provides the
    keywords that are available from those (properly caching data as needed).
    """

    @classmethod
    def get_robot_version(cls) -> str:
        from robotframework_ls.impl import robot_version

        return robot_version.get_robot_version()

    @classmethod
    def get_robot_major_version(cls) -> int:
        from robotframework_ls.impl import robot_version

        return robot_version.get_robot_major_version()

    @classmethod
    def get_internal_libspec_dir(cls) -> str:
        from robotframework_ls import robot_config

        home = robot_config.get_robotframework_ls_home()

        pyexe: Union[bytes, str] = sys.executable
        if isinstance(pyexe, bytes):
            pyexe = pyexe.decode("utf-8", "replace")

        digest: str = get_digest_from_string(pyexe)

        v = cls.get_robot_version()

        # Note: _v1: information on the mtime of the libspec sources now available.
        return os.path.join(home, "specs", cls.INTERNAL_VERSION, "%s_%s" % (digest, v))

    @classmethod
    def get_internal_builtins_libspec_dir(cls, internal_libspec_dir=None):
        return os.path.join(
            internal_libspec_dir or cls.get_internal_libspec_dir(), "builtins"
        )

    # On v2 we disambiguate by using a hash for the filenames if we're generating
    # a libspec for a target filename.
    INTERNAL_VERSION = "v2"

    def create_copy(self):
        return LibspecManager(
            builtin_libspec_dir=self._builtins_libspec_dir,
            user_libspec_dir=self._user_libspec_dir,
            dir_cache_dir=self._dir_cache_dir,
            observer=None,
            endpoint=None,
            pre_generate_libspecs=False,
            cache_libspec_dir=self._cache_libspec_dir,
            is_copy=True,
        )

    def __init__(
        self,
        builtin_libspec_dir: Optional[str] = None,
        user_libspec_dir: Optional[str] = None,
        dir_cache_dir: Optional[str] = None,
        observer: Optional[IFSObserver] = None,
        endpoint: Optional[IEndPoint] = None,
        pre_generate_libspecs: bool = False,
        cache_libspec_dir: Optional[str] = None,
        *,
        is_copy: bool = False,
    ):
        """
        :param __internal_libspec_dir__:
            Only to be used in tests (to regenerate the builtins)!
        """
        from robocorp_ls_core import watchdog_wrapper
        from robocorp_ls_core.cache import DirCache
        from robotframework_ls import robot_config

        self._is_copy = is_copy
        self._dir_cache_dir = dir_cache_dir or os.path.join(
            robot_config.get_robotframework_ls_home(), ".cache"
        )
        dir_cache = DirCache(self._dir_cache_dir)

        self._libspec_dir = self.get_internal_libspec_dir()

        self._user_libspec_dir = user_libspec_dir or os.path.join(
            self._libspec_dir, "user"
        )
        self._cache_libspec_dir = cache_libspec_dir or os.path.join(
            self._libspec_dir, "cache"
        )
        self._builtins_libspec_dir = (
            builtin_libspec_dir
            or self.get_internal_builtins_libspec_dir(self._libspec_dir)
        )
        log.info("User libspec dir: %s", self._user_libspec_dir)
        log.info("Builtins libspec dir: %s", self._builtins_libspec_dir)
        log.info("Cache libspec dir: %s", self._cache_libspec_dir)

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
        try:
            os.makedirs(self._cache_libspec_dir)
        except:
            # Ignore exception if it's already created.
            pass

        self.pre_generate_libspecs = pre_generate_libspecs

        if pre_generate_libspecs:
            from robotframework_ls.impl.libspec_markdown_conversion import (
                LibspecMarkdownConversion,
            )

            self.libspec_markdown_conversion: Optional[
                LibspecMarkdownConversion
            ] = LibspecMarkdownConversion(self)
        else:
            self.libspec_markdown_conversion = None

        self._libspec_warmup = LibspecWarmup(endpoint, dir_cache)

        self._libspec_failures_cache: Dict[
            tuple, str
        ] = {}  # key -> error creating libspec

        self._main_thread = threading.current_thread()

        if observer is None:
            from robocorp_ls_core.watchdog_wrapper import create_observer

            log.info("No observer passed to LibspecManager (creating dummy observer).")

            observer = create_observer("dummy", ())
        self._fs_observer = observer

        self._file_changes_notifier = watchdog_wrapper.create_notifier(
            self._on_file_changed, timeout=0.5, extensions=(".libspec", ".py")
        )

        # Spec info found in the workspace
        self._workspace_folder_uri_to_folder_info: Dict[str, _FolderInfo] = {}
        self._additional_pythonpath_folder_to_folder_info: Dict[str, _FolderInfo] = {}

        # Spec info found in the pythonpath
        pythonpath_folder_to_folder_info: Dict[str, _FolderInfo] = {}
        found = set()
        for path in sys.path:
            if path:
                try:
                    resolved = Path(path).resolve()  # also solves links.
                except:
                    log.exception(
                        f"Unable to Path.resolve({path!r}) (resolving PYTHONPATH entries)."
                    )
                    continue

                if resolved in found:
                    continue
                found.add(resolved)
                if os.path.isdir(path):
                    pythonpath_folder_to_folder_info[path] = _FolderInfo(
                        path, recursive=False
                    )

        self._pythonpath_folder_to_folder_info: Dict[
            str, _FolderInfo
        ] = pythonpath_folder_to_folder_info

        # Spec info found in internal dirs (autogenerated)
        self._internal_folder_to_folder_info: Dict[str, _FolderInfo] = {
            self._user_libspec_dir: _FolderInfo(
                self._user_libspec_dir, recursive=False
            ),
            self._builtins_libspec_dir: _FolderInfo(
                self._builtins_libspec_dir, recursive=False
            ),
        }

        # Must be set from the outside world when needed.
        self.config = None

        if self.pre_generate_libspecs:
            log.debug("Generating builtin libraries libspec.")
            self._libspec_warmup.gen_builtin_libraries(self)

        log.debug("Synchronizing internal caches.")
        self._synchronize()
        log.debug("Finished initializing LibspecManager.")

    @property
    def is_copy(self):
        return self._is_copy

    def schedule_conversion_to_markdown(self, spec_filename: str):
        if self.libspec_markdown_conversion is not None:
            self.libspec_markdown_conversion.schedule_conversion_to_markdown(
                spec_filename
            )

    @property
    def fs_observer(self) -> IFSObserver:
        return self._fs_observer

    def _check_in_main_thread(self):
        curr_thread = threading.current_thread()
        if self._main_thread is not curr_thread:
            raise AssertionError(
                f"This may only be called at the thread: {self._main_thread}. Current thread: {curr_thread}"
            )

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_LIBRARIES_LIBDOC_PRE_GENERATE,
        )
        from robocorp_ls_core.basic import make_unique

        self._check_in_main_thread()
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

        self._config = config
        existing_entries = set(self._additional_pythonpath_folder_to_folder_info.keys())
        if config is not None:
            pythonpath_entries = set(
                config.get_setting(OPTION_ROBOT_PYTHONPATH, list, [])
            )
            for new_pythonpath_entry in pythonpath_entries:
                new_pythonpath_entry = os.path.abspath(new_pythonpath_entry)

                if new_pythonpath_entry not in existing_entries:
                    self.add_additional_pythonpath_folder(new_pythonpath_entry)
            for old_entry in existing_entries:
                if old_entry not in pythonpath_entries:
                    self.remove_additional_pythonpath_folder(old_entry)

            pre_generate = []
            pre_generate.extend(
                config.get_setting(OPTION_ROBOT_LIBRARIES_LIBDOC_PRE_GENERATE, list, [])
            )

            if self.pre_generate_libspecs:
                log.debug("Generating user/pythonpath libraries libspec.")
                self._libspec_warmup.gen_user_libraries(self, make_unique(pre_generate))

    @property
    def user_libspec_dir(self) -> str:
        return self._user_libspec_dir

    @property
    def cache_libspec_dir(self) -> str:
        return self._cache_libspec_dir

    def _on_file_changed(self, spec_file, folder_info_on_change_spec):
        log.debug("File change detected: %s", spec_file)

        # Check if the cache related to libspec generation failure must be
        # cleared.
        fix = False
        for cache_key in self._libspec_failures_cache:
            libname = cache_key[0]
            if libname in spec_file:
                fix = True
                break
        if fix:
            new = {}
            for cache_key, value in self._libspec_failures_cache.items():
                libname = cache_key[0]
                if libname not in spec_file:
                    new[cache_key] = value
            # Always set as a whole (to avoid racing conditions).
            self._libspec_failures_cache = new

        # Notify _FolderInfo._on_change_spec
        if spec_file.lower().endswith(".libspec"):
            folder_info_on_change_spec(spec_file)

    def add_workspace_folder(self, folder_uri: str):
        self._check_in_main_thread()
        from robocorp_ls_core import uris

        if folder_uri not in self._workspace_folder_uri_to_folder_info:
            log.debug("Added workspace folder: %s", folder_uri)
            cp = self._workspace_folder_uri_to_folder_info.copy()
            folder_info = cp[folder_uri] = _FolderInfo(
                uris.to_fs_path(folder_uri), recursive=True
            )
            self._workspace_folder_uri_to_folder_info = cp
            folder_info.start_watch(self._fs_observer, self._file_changes_notifier)
            folder_info.synchronize()
        else:
            log.debug("Workspace folder already added: %s", folder_uri)

    def remove_workspace_folder(self, folder_uri: str):
        self._check_in_main_thread()
        if folder_uri in self._workspace_folder_uri_to_folder_info:
            log.debug("Removed workspace folder: %s", folder_uri)
            cp = self._workspace_folder_uri_to_folder_info.copy()
            folder_info = cp.pop(folder_uri, NULL)
            folder_info.dispose()
            self._workspace_folder_uri_to_folder_info = cp
        else:
            log.debug("Workspace folder already removed: %s", folder_uri)

    def add_additional_pythonpath_folder(self, folder_path):
        self._check_in_main_thread()
        if folder_path not in self._additional_pythonpath_folder_to_folder_info:
            log.debug("Added additional pythonpath folder: %s", folder_path)
            cp = self._additional_pythonpath_folder_to_folder_info.copy()
            folder_info = cp[folder_path] = _FolderInfo(folder_path, recursive=True)
            self._additional_pythonpath_folder_to_folder_info = cp
            folder_info.start_watch(self._fs_observer, self._file_changes_notifier)
            folder_info.synchronize()
        else:
            log.debug("Additional pythonpath folder already added: %s", folder_path)

    def remove_additional_pythonpath_folder(self, folder_path):
        self._check_in_main_thread()
        if folder_path in self._additional_pythonpath_folder_to_folder_info:
            log.debug("Removed additional pythonpath folder: %s", folder_path)
            cp = self._additional_pythonpath_folder_to_folder_info.copy()
            folder_info = cp.pop(folder_path, NULL)
            folder_info.dispose()
            self._additional_pythonpath_folder_to_folder_info = cp
        else:
            log.debug("Additional pythonpath folder already removed: %s", folder_path)

    def synchronize_workspace_folders(self):
        for folder_info in self._workspace_folder_uri_to_folder_info.values():
            folder_info.start_watch(self._fs_observer, self._file_changes_notifier)
            folder_info.synchronize()

    def synchronize_pythonpath_folders(self):
        for folder_info in self._pythonpath_folder_to_folder_info.values():
            folder_info.start_watch(self._fs_observer, self._file_changes_notifier)
            folder_info.synchronize()

    def synchronize_additional_pythonpath_folders(self):
        for folder_info in self._additional_pythonpath_folder_to_folder_info.values():
            folder_info.start_watch(self._fs_observer, self._file_changes_notifier)
            folder_info.synchronize()

    def synchronize_internal_libspec_folders(self):
        for folder_info in self._internal_folder_to_folder_info.values():
            folder_info.start_watch(self._fs_observer, self._file_changes_notifier)
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
        self.synchronize_additional_pythonpath_folders()
        self.synchronize_internal_libspec_folders()

    def collect_all_tracked_folders(self) -> Iterator[str]:
        from robocorp_ls_core import uris

        for uri in self._workspace_folder_uri_to_folder_info.keys():
            yield uris.to_fs_path(uri)

        yield from self._pythonpath_folder_to_folder_info.keys()

        yield from self._additional_pythonpath_folder_to_folder_info.keys()

    def iter_lib_info(self, builtin=False):
        """
        :rtype: generator(_LibInfo)
        """
        # Note: the iteration order is important (first ones are visited earlier
        # and have higher priority).
        iter_in = []
        for (_uri, info) in self._workspace_folder_uri_to_folder_info.items():
            if info.libspec_canonical_filename_to_info:
                iter_in.append((info.libspec_canonical_filename_to_info, False))

        for (_uri, info) in self._pythonpath_folder_to_folder_info.items():
            if info.libspec_canonical_filename_to_info:
                iter_in.append((info.libspec_canonical_filename_to_info, False))

        for (_uri, info) in self._additional_pythonpath_folder_to_folder_info.items():
            if info.libspec_canonical_filename_to_info:
                iter_in.append((info.libspec_canonical_filename_to_info, False))

        if builtin:
            info = self._internal_folder_to_folder_info[self._builtins_libspec_dir]
            if info.libspec_canonical_filename_to_info:
                iter_in.append((info.libspec_canonical_filename_to_info, True))
        else:
            for (_uri, info) in self._internal_folder_to_folder_info.items():
                if info.libspec_canonical_filename_to_info:
                    iter_in.append((info.libspec_canonical_filename_to_info, True))

        for canonical_filename_to_info, can_regenerate in iter_in:
            for canonical_spec_filename, info in list(
                canonical_filename_to_info.items()
            ):

                if info is None:
                    info = canonical_filename_to_info[
                        canonical_spec_filename
                    ] = _load_lib_info(self, canonical_spec_filename, can_regenerate)

                # Note: we could end up yielding a library with the same name
                # multiple times due to its scope. It's up to the caller to
                # validate that.
                if info is not None and info.library_doc is not None:
                    yield info

    def get_library_names(self):
        return sorted(
            set(lib_info.library_doc.name for lib_info in self.iter_lib_info())
        )

    def _get_cached_error(
        self,
        libname,
        *,
        is_builtin=False,
        target_file: Optional[str] = None,
        args: Optional[str] = None,
    ) -> Optional[str]:
        cache_key = (libname, is_builtin, target_file, args)
        return self._libspec_failures_cache.get(cache_key)

    def _create_libspec(
        self,
        libname,
        *,
        is_builtin=False,
        target_file: Optional[str] = None,
        args: Optional[str] = None,
    ) -> Optional[str]:
        """
        :param target_file:
            If given this is the library file (i.e.: c:/foo/bar.py) which is the
            actual library we're creating the spec for.
        """
        cache_key = (libname, is_builtin, target_file, args)
        previous = self._libspec_failures_cache.get(cache_key, Sentinel.SENTINEL)
        if previous is not Sentinel.SENTINEL:
            return typing.cast(Optional[str], previous)

        error_creating = self._cached_create_libspec(
            libname, is_builtin, target_file, args
        )
        if error_creating is not None:
            # Always set as a whole (to avoid racing conditions).
            cp = self._libspec_failures_cache.copy()
            cp[cache_key] = error_creating
            self._libspec_failures_cache = cp

        return error_creating

    def _subprocess_check_output(self, *args, **kwargs):
        # Only done for mocking.
        from robocorp_ls_core.subprocess_wrapper import subprocess

        return subprocess.check_output(*args, **kwargs)

    def _cached_create_libspec(
        self,
        libname: str,
        is_builtin: bool,
        target_file: Optional[str],
        args: Optional[str],
        *,
        _internal_force_text=False,  # Should only be set from within this function.
    ) -> Optional[str]:
        """
        Returns an error message if it wasn't able to generate it or None if
        it did generate it.
        """
        from robotframework_ls.impl import robot_constants

        if not is_builtin:
            if not target_file:
                is_builtin = libname in robot_constants.STDLIBS

        import time
        from robocorp_ls_core.subprocess_wrapper import subprocess
        from robocorp_ls_core.robotframework_log import get_log_level

        acquire_mutex = _timed_acquire_mutex_for_spec_filename

        if _internal_force_text:
            # In this case this is a recursive call and we already have the lock.
            acquire_mutex = NULL

        log_exception = log.exception
        if is_builtin and libname == "Dialogs" and get_log_level() < 1:
            # Dialogs may have dependencies that are not available, so, don't show
            # it unless verbose mode is enabled.
            log_exception = log.debug

        if not libname.replace(".", "").replace("/", "").replace("\\", "").strip():
            return f"Unable to generate libspec for: {libname}"

        additional_path = None
        additional_path_exists = False

        log_time = True
        cwd = None

        if target_file is not None:
            additional_path = os.path.dirname(target_file)
            if os.path.splitext(os.path.basename(target_file))[0] == "__init__":
                additional_path = os.path.dirname(additional_path)

            additional_path_exists = os.path.exists(additional_path)
            if additional_path and additional_path_exists:
                cwd = additional_path
            if libname.endswith(("/", "\\")):
                libname = libname[:-1]
            libname = os.path.basename(libname)
            if libname.lower().endswith((".py", ".class", ".java")):
                libname = os.path.splitext(libname)[0]

        curtime = time.time()

        try:
            try:
                call = [sys.executable]
                major_version = self.get_robot_major_version()
                if major_version < 4:
                    call.extend("-m robot.libdoc --format XML".split())
                else:
                    call.extend(
                        "-m robot.libdoc --format XML --specdocformat RAW".split()
                    )

                if additional_path and additional_path_exists:
                    call.extend(["-P", os.path.normpath(additional_path)])

                if _internal_force_text:
                    call.append("--docformat")
                    call.append("text")

                # Note: always set as a whole, so, iterate in generator is thread-safe.
                for entry in self._additional_pythonpath_folder_to_folder_info:
                    if os.path.exists(entry):
                        call.extend(["-P", os.path.normpath(entry)])

                if not args:
                    call.append(libname)
                else:
                    call.append("::".join([libname, args]))

                libspec_filename = self._compute_libspec_filename(
                    libname, is_builtin, target_file, args
                )

                log.debug(f"Obtaining mutex to generate libspec: {libspec_filename}.")
                with acquire_mutex(libspec_filename):  # Could fail.
                    log.debug(
                        f"Obtained mutex to generate libspec: {libspec_filename}."
                    )
                    call.append(libspec_filename)

                    mtime: float = -1
                    try:
                        mtime = os.path.getmtime(libspec_filename)
                    except:
                        pass

                    log.debug(
                        "Generating libspec for: %s.\nCwd:%s\nCommand line:\n%s",
                        libname,
                        cwd,
                        " ".join(call),
                    )
                    try:
                        try:
                            # Note: stdout is always subprocess.PIPE in this call.
                            # Note: the env is always inherited (the process which has
                            # the LibspecManager must be the target env already).
                            self._subprocess_check_output(
                                call,
                                stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE,
                                cwd=cwd,
                            )
                        except OSError as e:
                            log.exception("Error calling: %s", call)
                            # We may have something as: Ignore OSError: [WinError 6] The handle is invalid,
                            # give the result based on whether the file changed on disk.
                            try:
                                if mtime != os.path.getmtime(libspec_filename):
                                    _dump_spec_filename_additional_info(
                                        self,
                                        libspec_filename,
                                        is_builtin=is_builtin,
                                        obtain_mutex=False,
                                    )
                                    return None
                            except:
                                pass

                            log.debug("Not retrying after OSError failure.")
                            return str(e)

                    except subprocess.CalledProcessError as e:
                        if not _internal_force_text:
                            if (
                                b"reST format requires 'docutils' module to be installed"
                                in e.output
                            ):
                                return self._cached_create_libspec(
                                    libname,
                                    is_builtin,
                                    target_file,
                                    args,
                                    _internal_force_text=True,
                                )

                        log_exception(
                            "Error creating libspec: %s.\nReturn code: %s\nOutput:\n%s",
                            libname,
                            e.returncode,
                            e.output,
                        )
                        bytes_output = e.output
                        output = bytes_output.decode("utf-8", "replace")

                        # Remove things we don't want to show.
                        for s in ("Try --help", "--help", "Traceback"):
                            index = output.find(s)
                            if index >= 0:
                                output = output[:index].strip()

                        if output:
                            return output
                        return f"Error creating libspec: {output}"

                    _dump_spec_filename_additional_info(
                        self,
                        libspec_filename,
                        is_builtin=is_builtin,
                        obtain_mutex=False,
                    )
                    return None
            except Exception as e:
                log_exception("Error creating libspec: %s", libname)
                return str(e)
        finally:
            if log_time:
                delta = time.time() - curtime
                log.debug("Took: %.2fs to generate info for: %s" % (delta, libname))

    def dispose(self):
        self._file_changes_notifier.dispose()
        if self.libspec_markdown_conversion is not None:
            self.libspec_markdown_conversion.dispose()

    def _compute_libspec_filename(
        self,
        libname: str,
        is_builtin: bool = False,
        target_file: Optional[str] = None,
        args: Optional[str] = None,
    ):
        from robotframework_ls.impl import robot_constants

        libspec_dir = self._user_libspec_dir
        if libname in robot_constants.STDLIBS:
            libspec_dir = self._builtins_libspec_dir

        if target_file:
            if args:
                digest = (
                    get_digest_from_string(target_file)
                    + "_"
                    + get_digest_from_string(args)
                )
            else:
                digest = get_digest_from_string(target_file)

            libspec_filename = os.path.join(libspec_dir, digest + ".libspec")
        elif not args:
            libspec_filename = os.path.join(libspec_dir, libname + ".libspec")
        else:
            digest = get_digest_from_string(args)
            libspec_filename = os.path.join(libspec_dir, libname + digest + ".libspec")
        return libspec_filename

    def _do_create_libspec_on_get(
        self, libname, target_file: Optional[str], args: Optional[str], is_builtin: bool
    ) -> Optional[str]:
        error_creating = self._create_libspec(
            libname, target_file=target_file, args=args, is_builtin=is_builtin
        )

        if error_creating is None:
            self.synchronize_internal_libspec_folders()
        return error_creating

    def _get_library_target_filename(
        self, libname: str, current_doc_uri: Optional[str] = None
    ) -> Optional[str]:
        from robocorp_ls_core import uris

        target_file: Optional[str] = None
        libname_lower = libname.lower()

        if os.path.isabs(libname):
            target_file = libname
        else:
            # Check if it maps to a file in the filesystem
            if current_doc_uri is not None:
                cwd = os.path.dirname(uris.to_fs_path(current_doc_uri))
                if cwd and os.path.isdir(cwd):
                    f = os.path.join(cwd, libname)
                    if os.path.isdir(f):
                        f = os.path.join(f, "__init__.py")

                    if os.path.exists(f):
                        target_file = f

                    elif not libname_lower.endswith(".py"):
                        f += ".py"
                        if os.path.exists(f):
                            target_file = f

            if target_file is None and libname.endswith((".py", ".class", ".java")):
                iter_in_pythonpath_directories = itertools.chain(
                    self._additional_pythonpath_folder_to_folder_info.keys(),
                    self._pythonpath_folder_to_folder_info.keys(),
                )

                # https://github.com/robocorp/robotframework-lsp/issues/266
                # If the user specifies a file, we don't just search the current
                # relative folder, we also need to search for relative entries
                # in the whole PYTHONPATH.
                for entry in iter_in_pythonpath_directories:
                    check_target = os.path.join(entry, libname)
                    if os.path.exists(check_target):
                        target_file = check_target
                        break

        return target_file

    def get_library_doc_or_error(
        self,
        libname: str,
        create: bool,
        completion_context: ICompletionContext,
        builtin: bool = False,
        args: Optional[str] = None,
    ) -> ILibraryDocOrError:
        """
        :param libname:
            It may be a library name, a relative path to a .py file or an
            absolute path to a .py file.
        """
        from robotframework_ls.impl import robot_constants
        from robotframework_ls.impl import ast_utils

        libname_lower = libname.lower()
        target_file: str = ""
        normalized_target_file: str = ""
        pre_error_msg: str = ""

        config = self.config
        libraries_libdoc_needs_args_lower: Set[str]
        if config is not None:
            libraries_libdoc_needs_args_lower = set(
                str(x).lower()
                for x in config.get_setting(
                    OPTION_ROBOT_LIBRARIES_LIBDOC_NEEDS_ARGS,
                    list,
                    ["remote", "fakerlib"],
                )
            )
        else:
            libraries_libdoc_needs_args_lower = {"remote", "fakerlib"}

        # Note that experimentally, using '*' may pass args to all libraries.
        if (
            libname_lower not in libraries_libdoc_needs_args_lower
            and "*" not in libraries_libdoc_needs_args_lower
        ):
            args = None

        if args:
            if "{" in args:
                # We need to resolve the arguments if there are variables in it.
                from robotframework_ls.impl.variable_resolve import (
                    ResolveVariablesContext,
                )

                assert completion_context.config is config

                args, unresolved = ResolveVariablesContext(
                    completion_context
                ).token_value_and_unresolved_resolving_variables(
                    ast_utils.create_token(args)
                )

                pre_error_msg = (
                    "It was not possible to statically resolve the following variables:\n%s\nFollow-up error:\n"
                    % (", ".join(str(x[0]) for x in unresolved),)
                )

            args = args.replace("\\\\", "\\")

        if not builtin:
            found_target_filename = self._get_library_target_filename(
                libname, completion_context.doc.uri
            )
            if found_target_filename:
                target_file = found_target_filename
                normalized_target_file = normalize_filename(target_file)
            else:
                builtin = libname in robot_constants.STDLIBS

        if libname_lower.endswith((".py", ".class", ".java")):
            libname_lower = os.path.splitext(libname_lower)[0]

        if "/" in libname_lower or "\\" in libname_lower:
            libname_lower = os.path.basename(libname_lower)

        lib_info: _LibInfo
        for lib_info in self.iter_lib_info(builtin=builtin):
            library_doc = lib_info.library_doc

            # If it maps to a file in the filesystem, that's what we need to match,
            # otherwise, match just by its name.
            # Note: this is only valid for the cases where we can regenerate the info
            # for cases where this information is builtin, only match by the name.
            if target_file and lib_info._can_regenerate:
                if args:
                    digest = (
                        get_digest_from_string(target_file)
                        + "_"
                        + get_digest_from_string(args)
                    )
                    found = library_doc.filename.endswith(digest + ".libspec")

                else:
                    found = bool(
                        library_doc.source
                        and normalize_filename(library_doc.source)
                        == normalized_target_file
                    )
                    if not found:
                        try:
                            found = bool(
                                library_doc.source
                                and os.path.samefile(library_doc.source, target_file)
                            )
                        except:
                            # os.path.samefile touches the filesystem, so, it can
                            # raise an exception.
                            found = False
            else:
                if not args:
                    found = bool(
                        library_doc.name and library_doc.name.lower() == libname_lower
                    )
                else:
                    digest = get_digest_from_string(args)
                    found = library_doc.filename.endswith(
                        os.path.normcase(libname + digest + ".libspec")
                    )

            if found:
                if not lib_info.verify_sources_sync():
                    if create:
                        # Found but it's not in sync. Try to regenerate (don't proceed
                        # because we don't want to match a lower priority item, so,
                        # regenerate and get from the cache without creating).
                        self._do_create_libspec_on_get(
                            libname, target_file, args, is_builtin=builtin
                        )

                        # Note: get even if it if was not created (we may match
                        # a lower priority library).
                        return self.get_library_doc_or_error(
                            libname,
                            create=False,
                            completion_context=completion_context,
                            builtin=builtin,
                            args=args,
                        )
                    else:
                        # Not in sync and it should not be created, just skip it.
                        continue
                else:
                    return _LibraryDocOrError(library_doc, None)

        if create:
            error_msg = self._do_create_libspec_on_get(
                libname, target_file, args, is_builtin=builtin
            )
            if error_msg is None:
                return self.get_library_doc_or_error(
                    libname,
                    create=False,
                    completion_context=completion_context,
                    builtin=builtin,
                    args=args,
                )
            return _LibraryDocOrError(None, pre_error_msg + error_msg)

        error_msg = self._get_cached_error(
            libname, is_builtin=builtin, target_file=target_file, args=args
        )
        if error_msg:
            log.debug("Unable to get library named: %s. Reason: %s", libname, error_msg)
            return _LibraryDocOrError(None, pre_error_msg + error_msg)

        msg = f"Unable to find library named: {libname}"
        log.debug(msg)
        return _LibraryDocOrError(None, pre_error_msg + msg)


class _LibraryDocOrError:
    def __init__(self, library_doc: Optional[ILibraryDoc], error: Optional[str]):
        self.library_doc = library_doc
        self.error = error

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: ILibraryDocOrError = check_implements(self)
