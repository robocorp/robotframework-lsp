# Original work Copyright (c) 2004-2020 Holger Krekel and others (MIT)
# From https://github.com/pytest-dev/pytest
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Robocorp Technologies Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit
import contextlib
import itertools
import os
import shutil
import sys
import uuid
import warnings
from functools import partial
from typing import Iterable, Iterator, TypeVar, Optional


from pathlib import Path, PurePath
import weakref
from robocorp_ls_core.protocols import ITimeoutHandle

__all__ = ["Path", "PurePath"]


LOCK_TIMEOUT = 60 * 60 * 3


_AnyPurePath = TypeVar("_AnyPurePath", bound=PurePath)


def get_lock_path(path: _AnyPurePath) -> _AnyPurePath:
    return path.joinpath(".lock")


def on_rm_rf_error(func, path: str, exc, *, start_path: Path) -> bool:
    """Handles known read-only errors during rmtree.

    The returned value is used only by our own tests.
    """
    exctype, excvalue = exc[:2]

    # another process removed the file in the middle of the "rm_rf" (xdist for example)
    # more context: https://github.com/pytest-dev/pytest/issues/5974#issuecomment-543799018
    if isinstance(excvalue, FileNotFoundError):
        return False

    if not isinstance(excvalue, PermissionError):
        warnings.warn(
            "(rm_rf) error removing {}\n{}: {}".format(path, exctype, excvalue)
        )
        return False

    if func not in (os.rmdir, os.remove, os.unlink):
        if func not in (os.open,):
            warnings.warn(
                "(rm_rf) unknown function {} when removing {}:\n{}: {}".format(
                    func, path, exctype, excvalue
                )
            )
        return False

    # Chmod + retry.
    import stat

    def chmod_rw(p: str) -> None:
        mode = os.stat(p).st_mode
        os.chmod(p, mode | stat.S_IRUSR | stat.S_IWUSR)

    # For files, we need to recursively go upwards in the directories to
    # ensure they all are also writable.
    p = Path(path)
    if p.is_file():
        for parent in p.parents:
            chmod_rw(str(parent))
            # stop when we reach the original path passed to rm_rf
            if parent == start_path:
                break
    chmod_rw(str(path))

    func(path)
    return True


def ensure_extended_length_path(path: Path) -> Path:
    """Get the extended-length version of a path (Windows).

    On Windows, by default, the maximum length of a path (MAX_PATH) is 260
    characters, and operations on paths longer than that fail. But it is possible
    to overcome this by converting the path to "extended-length" form before
    performing the operation:
    https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file#maximum-path-length-limitation

    On Windows, this function returns the extended-length absolute version of path.
    On other platforms it returns path unchanged.
    """
    if sys.platform.startswith("win32"):
        path = path.resolve()
        path = Path(get_extended_length_path_str(str(path)))
    return path


def get_extended_length_path_str(path: str) -> str:
    """Converts to extended length path as a str"""
    long_path_prefix = "\\\\?\\"
    unc_long_path_prefix = "\\\\?\\UNC\\"
    if path.startswith((long_path_prefix, unc_long_path_prefix)):
        return path
    # UNC
    if path.startswith("\\\\"):
        return unc_long_path_prefix + path[2:]
    return long_path_prefix + path


def rm_rf(path: Path) -> None:
    """Remove the path contents recursively, even if some elements
    are read-only.
    """
    path = ensure_extended_length_path(path)
    onerror = partial(on_rm_rf_error, start_path=path)
    shutil.rmtree(str(path), onerror=onerror)


def find_prefixed(root: Path, prefix: str) -> Iterator[Path]:
    """finds all elements in root that begin with the prefix, case insensitive"""
    l_prefix = prefix.lower()
    for x in root.iterdir():
        if x.name.lower().startswith(l_prefix):
            yield x


def extract_suffixes(iter: Iterable[PurePath], prefix: str) -> Iterator[str]:
    """
    :param iter: iterator over path names
    :param prefix: expected prefix of the path names
    :returns: the parts of the paths following the prefix
    """
    p_len = len(prefix)
    for p in iter:
        yield p.name[p_len:]


def find_suffixes(root: Path, prefix: str) -> Iterator[str]:
    """combines find_prefixes and extract_suffixes
    """
    return extract_suffixes(find_prefixed(root, prefix), prefix)


def parse_num(maybe_num) -> int:
    """parses number path suffixes, returns -1 on error"""
    try:
        return int(maybe_num)
    except ValueError:
        return -1


def make_numbered_dir(root: Path, prefix: str) -> Path:
    """create a directory with an increased number as suffix for the given prefix"""
    from robocorp_ls_core.system_mutex import generate_mutex_name
    from robocorp_ls_core.system_mutex import timed_acquire_mutex

    with timed_acquire_mutex(generate_mutex_name(f"generate_numbered{root}")):
        max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
        new_number = max_existing + 1
        new_path = root.joinpath("{}{}".format(prefix, new_number))
        new_path.mkdir()
        return new_path


def create_cleanup_lock(p: Path) -> Path:
    """crates a lock to prevent premature folder cleanup"""
    lock_path = get_lock_path(p)
    try:
        fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as e:
        raise OSError("cannot create lockfile in {path}".format(path=p)) from e
    else:
        pid = os.getpid()
        spid = str(pid).encode()
        os.write(fd, spid)
        os.close(fd)
        if not lock_path.is_file():
            raise OSError("lock path got renamed after successful creation")
        return lock_path


def register_cleanup_lock_removal(lock_path: Path, register=atexit.register):
    """registers a cleanup function for removing a lock, by default on atexit"""
    pid = os.getpid()

    def cleanup_on_exit(lock_path: Path = lock_path, original_pid: int = pid) -> None:
        current_pid = os.getpid()
        if current_pid != original_pid:
            # fork
            return
        try:
            lock_path.unlink()
        except OSError:
            pass

    return register(cleanup_on_exit)


def maybe_delete_a_numbered_dir(path: Path) -> None:
    """removes a numbered directory if its lock can be obtained and it does not seem to be in use"""
    path = ensure_extended_length_path(path)
    lock_path = None
    try:
        lock_path = create_cleanup_lock(path)
        parent = path.parent

        garbage = parent.joinpath("garbage-{}".format(uuid.uuid4()))
        path.rename(garbage)
        rm_rf(garbage)
    except OSError:
        #  known races:
        #  * other process did a cleanup at the same time
        #  * deletable folder was found
        #  * process cwd (Windows)
        return
    finally:
        # if we created the lock, ensure we remove it even if we failed
        # to properly remove the numbered dir
        if lock_path is not None:
            try:
                lock_path.unlink()
            except OSError:
                pass


def ensure_deletable(path: Path, consider_lock_dead_if_created_before: float) -> bool:
    """checks if `path` is deletable based on whether the lock file is expired"""
    if path.is_symlink():
        return False
    lock = get_lock_path(path)
    try:
        if not lock.is_file():
            return True
    except OSError:
        # we might not have access to the lock file at all, in this case assume
        # we don't have access to the entire directory (#7491).
        return False
    try:
        lock_time = lock.stat().st_mtime
    except Exception:
        return False
    else:
        if lock_time < consider_lock_dead_if_created_before:
            # wa want to ignore any errors while trying to remove the lock such as:
            # - PermissionDenied, like the file permissions have changed since the lock creation
            # - FileNotFoundError, in case another pytest process got here first.
            # and any other cause of failure.
            with contextlib.suppress(OSError):
                lock.unlink()
                return True
        return False


def try_cleanup(path: Path, consider_lock_dead_if_created_before: float) -> None:
    """tries to cleanup a folder if we can ensure it's deletable"""
    if ensure_deletable(path, consider_lock_dead_if_created_before):
        maybe_delete_a_numbered_dir(path)


def cleanup_candidates(root: Path, prefix: str, keep: int) -> Iterator[Path]:
    """lists candidates for numbered directories to be removed - follows py.path"""
    max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
    max_delete = max_existing - keep
    paths = find_prefixed(root, prefix)
    paths, paths2 = itertools.tee(paths)
    numbers = map(parse_num, extract_suffixes(paths2, prefix))
    for path, number in zip(paths, numbers):
        if number <= max_delete:
            yield path


def cleanup_numbered_dir(
    root: Path, prefix: str, keep: int, consider_lock_dead_if_created_before: float
) -> None:
    """cleanup for lock driven numbered directories"""
    for path in cleanup_candidates(root, prefix, keep):
        try_cleanup(path, consider_lock_dead_if_created_before)
    for path in root.glob("garbage-*"):
        try_cleanup(path, consider_lock_dead_if_created_before)


_handles: "weakref.WeakSet[ITimeoutHandle]" = weakref.WeakSet()


@atexit.register
def _exec_handles_now():
    for handle in _handles:
        handle.exec_on_timeout()


def register_to_call_on_timeout(func, *args, **kwargs):
    from robocorp_ls_core.timeouts import TimeoutTracker

    timeout_tracker = TimeoutTracker.get_singleton()
    handle = timeout_tracker.call_on_timeout(20, partial(func, *args, **kwargs))
    _handles.add(handle)
    atexit.register(func, *args, **kwargs)


def make_numbered_dir_with_cleanup(
    root: Path, prefix: str, keep: int, lock_timeout: float, register=None
) -> Path:
    """creates a numbered dir with a cleanup lock and removes old ones"""
    if register is None:
        register = register_to_call_on_timeout
    e = None
    for _i in range(10):
        try:
            p = make_numbered_dir(root, prefix)
            lock_path = create_cleanup_lock(p)
            # Note: register here is always atexit to remove lock file.
            register_cleanup_lock_removal(lock_path)
        except Exception as exc:
            e = exc
        else:
            consider_lock_dead_if_created_before = p.stat().st_mtime - lock_timeout
            # Register a cleanup for program exit
            register(
                cleanup_numbered_dir,
                root,
                prefix,
                keep,
                consider_lock_dead_if_created_before,
            )
            return p
    assert e is not None
    raise e


def get_user() -> Optional[str]:
    """Return the current user name, or None if getuser() does not work
    in the current environment (see #1010).
    """
    try:
        import getpass

        return getpass.getuser()
    except (ImportError, KeyError):
        return None
