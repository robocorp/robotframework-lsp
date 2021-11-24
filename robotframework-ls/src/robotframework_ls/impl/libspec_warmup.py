from robocorp_ls_core.robotframework_log import get_logger
import os
from robocorp_ls_core.protocols import IEndPoint, IDirCache
from typing import Optional, List, Any, Tuple, Callable, Iterable
from robocorp_ls_core.constants import NULL
from functools import partial

log = get_logger(__name__)


def _normfile(filename):
    return os.path.abspath(os.path.normpath(os.path.normcase(filename)))


def _norm_filename(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


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
        provide_args_and_kwargs_to_create_libspec: Callable[
            [], Iterable[Tuple[tuple, dict]]
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

            with ctx as progress_reporter:
                import time
                from concurrent import futures
                from robocorp_ls_core.system_mutex import timed_acquire_mutex
                from robocorp_ls_core.system_mutex import generate_mutex_name

                progress_wrapper = ProgressWrapperForTotalWork(progress_reporter)

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
                        log.debug(f"Obtained mutex to {progress_title}.")
                        for (
                            args_and_kwargs
                        ) in provide_args_and_kwargs_to_create_libspec():
                            progress_wrapper.increment_total_steps()

                            def progress_and_create(args_and_kwargs):
                                args, kwargs = args_and_kwargs
                                libspec_manager._create_libspec(*args, **kwargs)
                                progress_wrapper.increment_step_done()

                            wait_for.append(
                                thread_pool.submit(
                                    partial(progress_and_create, args_and_kwargs)
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
            log.info(f"Finished {progress_title}.")

    def gen_builtin_libraries(self, libspec_manager) -> None:
        """
        Generates .libspec files for the libraries builtin (if needed).
        """
        from robotframework_ls.impl import robot_constants
        from robotframework_ls.impl.robot_constants import RESERVED_LIB

        def provide_args_and_kwargs_to_create_libspec():
            for libname in robot_constants.STDLIBS:
                if libname == RESERVED_LIB:
                    continue
                builtins_libspec_dir = libspec_manager._builtins_libspec_dir
                if not os.path.exists(
                    os.path.join(builtins_libspec_dir, f"{libname}.libspec")
                ):
                    yield (libname,), dict(is_builtin=True)

        self._generate(
            libspec_manager,
            progress_title="Generate .libspec for builtin libraries",
            elapsed_time_key="generate_builtins_libspec",
            mutex_name_prefix="gen_builtins_",
            on_finish=lambda: None,
            provide_args_and_kwargs_to_create_libspec=provide_args_and_kwargs_to_create_libspec,
        )

    def gen_user_libraries(self, libspec_manager, user_libraries: List[str]):
        for name in user_libraries:
            libspec_manager._create_libspec(name)
        libspec_manager.synchronize_internal_libspec_folders()
