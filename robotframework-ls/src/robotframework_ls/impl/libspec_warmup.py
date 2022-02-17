from robocorp_ls_core.robotframework_log import get_logger
import os
from robocorp_ls_core.protocols import IEndPoint, IDirCache
from typing import (
    Optional,
    List,
    Any,
    Tuple,
    Callable,
    Iterable,
    Dict,
    Iterator,
    Set,
)
from robocorp_ls_core.constants import NULL
from functools import partial
import threading
from robotframework_ls.impl.robot_lsp_constants import CHECK_IF_LIBRARIES_INSTALLED
from robocorp_ls_core.basic import normalize_filename

log = get_logger(__name__)


def _normfile(filename):
    return normalize_filename(filename)


def _norm_filename(path):
    return normalize_filename(os.path.realpath(path))


class _Node(object):
    def __init__(self, name: str) -> None:
        self.name = name
        self._children: Dict[str, _Node] = {}
        self.is_leaf_libname = False
        self.full_libname = ""

    def __str__(self):
        return f"_Node({self.name})"

    __repr__ = __str__

    def add_child(self, name: str) -> "_Node":
        c = self._children.get(name)
        if c is None:  # If it exists, just reuse it.
            c = self._children[name] = _Node(name)
        return c

    def get_child(self, name: str) -> Optional["_Node"]:
        return self._children.get(name)

    def has_children(self):
        return len(self._children) > 0


class LibspecWarmup(object):
    """
    This class pre-generates the .libspec files as needed.

    Note that it's a "friend" of LibspecManager and may access its internal apis.
    """

    def __init__(
        self,
        endpoint: Optional[IEndPoint] = None,
        dir_cache: Optional[IDirCache] = None,
    ):
        self._endpoint = endpoint
        self._dir_cache = dir_cache

    def _generate(
        self,
        libspec_manager,
        progress_title: str,
        elapsed_time_key: Optional[str],
        mutex_name_prefix: str,
        on_finish: Callable[[], Any],
        provide_libname_and_kwargs_to_create_libspec: Callable[
            [], Iterable[Tuple[str, dict]]
        ],
    ):
        from robocorp_ls_core.progress_report import progress_context
        from robocorp_ls_core.progress_report import ProgressWrapperForTotalWork

        try:
            ctx: Any
            if self._endpoint is not None:
                ctx = progress_context(
                    self._endpoint,
                    progress_title,
                    self._dir_cache,
                    elapsed_time_key=elapsed_time_key,
                )
            else:
                ctx = NULL

            import time
            from concurrent import futures
            from robocorp_ls_core.system_mutex import timed_acquire_mutex
            from robocorp_ls_core.system_mutex import generate_mutex_name

            initial_time = time.time()
            wait_for = []

            max_workers = min(10, (os.cpu_count() or 1) + 4)
            thread_pool = futures.ThreadPoolExecutor(max_workers=max_workers)

            try:
                log.debug(f"Waiting for mutex to {progress_title}.")
                with timed_acquire_mutex(
                    generate_mutex_name(
                        _norm_filename(libspec_manager._builtins_libspec_dir),
                        prefix=mutex_name_prefix,
                    ),
                    timeout=100,
                ):
                    library_names = set(libspec_manager.get_library_names())

                    with ctx as progress_reporter:
                        progress_wrapper = ProgressWrapperForTotalWork(
                            progress_reporter
                        )

                        log.debug(f"Obtained mutex to {progress_title}.")
                        for (
                            libname,
                            kwargs,
                        ) in provide_libname_and_kwargs_to_create_libspec():
                            libspec_filename = (
                                libspec_manager._compute_libspec_filename(
                                    libname, **kwargs
                                )
                            )
                            if (
                                os.path.exists(libspec_filename)
                                or libname in library_names
                            ):
                                continue
                            progress_wrapper.increment_total_steps()

                            def progress_and_create(libname, kwargs):
                                libspec_manager._create_libspec(libname, **kwargs)
                                progress_wrapper.increment_step_done()

                            wait_for.append(
                                thread_pool.submit(
                                    partial(progress_and_create, libname, kwargs)
                                )
                            )

                        for future in wait_for:
                            future.result()

                        if wait_for:
                            log.debug(
                                "Total time to %s: %.2fs"
                                % (progress_title, time.time() - initial_time)
                            )
                            on_finish()
            finally:
                thread_pool.shutdown(wait=False)
        except:
            log.exception(f"Error {progress_title}.")
        finally:
            log.debug(f"Finished {progress_title}.")

    def gen_builtin_libraries(self, libspec_manager) -> None:
        """
        Generates .libspec files for the libraries builtin (if needed).
        """
        from robotframework_ls.impl import robot_constants
        from robotframework_ls.impl.robot_constants import RESERVED_LIB

        def provide_libname_and_kwargs_to_create_libspec():
            for libname in robot_constants.STDLIBS:
                if libname == RESERVED_LIB:
                    continue
                yield libname, dict(is_builtin=True)

        self._generate(
            libspec_manager,
            progress_title="Generate .libspec for builtin libraries",
            elapsed_time_key="generate_builtins_libspec",
            mutex_name_prefix="gen_builtins_",
            on_finish=lambda: None,
            provide_libname_and_kwargs_to_create_libspec=provide_libname_and_kwargs_to_create_libspec,
        )

    def find_rf_libraries(
        self,
        libspec_manager,
        target_libs: Iterable[str] = CHECK_IF_LIBRARIES_INSTALLED,
        tracked_folders=None,
    ) -> Set[str]:
        """
        Given an input of target libraries, try to discover if those are available
        in the PYTHONPATH.
        """

        root = _Node("")
        for libname in target_libs:
            splitted = libname.split(".")
            assert splitted
            parent = root

            for name in splitted:
                parent = parent.add_child(name)

            # The last one is marked as being an actual entry.
            parent.is_leaf_libname = True
            parent.full_libname = libname

        found_libnames: Set[str] = set()
        if tracked_folders is None:
            tracked_folders = libspec_manager.collect_all_tracked_folders()
        for s in tracked_folders:
            if os.path.isdir(s):
                found_libnames.update(self._veriy_tree_match(root, s, True))

        return found_libnames

    def _veriy_tree_match(
        self, parent: _Node, path: str, is_dir: bool
    ) -> Iterator[str]:
        try:
            if parent.has_children():
                if is_dir:
                    for dir_entry in os.scandir(path):
                        if dir_entry.is_dir():
                            use_name = dir_entry.name
                        else:
                            use_name = dir_entry.name
                            if not use_name.endswith(".py"):
                                continue
                            use_name = os.path.splitext(use_name)[0]

                        child_node = parent.get_child(use_name)
                        if child_node is not None:
                            if child_node.is_leaf_libname:
                                yield child_node.full_libname

                            yield from self._veriy_tree_match(
                                child_node, dir_entry.path, dir_entry.is_dir()
                            )
        except:
            log.exception(
                f"Exception handled while computing preinstalled libraries when verifying: {path}"
            )

    def gen_user_libraries(self, libspec_manager, user_libraries: List[str]):
        """
        Pre-generate the libspec for user libraries installed (in a thread).

        Note that it'll do it for the libraries that the user pre-specifies as well
        as those we automatically find in the PYTHONPATH.

        :param user_libraries:
            The libraries that the user specifies.
        """

        def provide_libname_and_kwargs_to_create_libspec():
            for libname in user_libraries:
                yield libname, {}

            if os.environ.get(
                "ROBOTFRAMEWORK_LS_PRE_GENERATE_PYTHONPATH_LIBS", ""
            ).lower() not in (
                "0",
                "false",
            ):
                # Now, besides those (specified by the user), we'll also try to find
                # existing libraries in the PYTHONPATH. Note that it's possible to
                # set an environment variable such as:
                # ROBOTFRAMEWORK_LS_PRE_GENERATE_PYTHONPATH_LIBS=0
                # to skip this process.
                for libname in self.find_rf_libraries(libspec_manager):
                    yield libname, {}

        def in_thread():
            self._generate(
                libspec_manager,
                progress_title="Generate .libspec for libraries",
                elapsed_time_key="generate_libspec",
                mutex_name_prefix="gen_libspec_",
                on_finish=libspec_manager.synchronize_internal_libspec_folders,
                provide_libname_and_kwargs_to_create_libspec=provide_libname_and_kwargs_to_create_libspec,
            )

        t = threading.Thread(target=in_thread)
        t.daemon = True
        t.start()
