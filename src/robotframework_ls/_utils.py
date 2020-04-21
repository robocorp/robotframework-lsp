# Original work Copyright 2017 Palantir Technologies, Inc. (MIT)
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
import functools
import inspect
import os
import sys
import threading

from robotframework_ls.constants import IS_PY2
from contextlib import contextmanager
from robotframework_ls.options import DEFAULT_TIMEOUT
from robotframework_ls.robotframework_log import get_logger

try:
    TimeoutError = TimeoutError  # @ReservedAssignment
except NameError:

    class TimeoutError(RuntimeError):  # @ReservedAssignment
        pass


PARENT_PROCESS_WATCH_INTERVAL = 3  # 3 s

if IS_PY2:
    import pathlib2 as pathlib

    def as_str(s):
        if isinstance(s, unicode):
            return s.encode("utf-8", "replace")
        return s


else:
    import pathlib

    def as_str(s):
        if isinstance(s, bytes):
            return s.decode("utf-8", "replace")
        return s


log = get_logger(__name__)


def debounce(interval_s, keyed_by=None):
    """Debounce calls to this function until interval_s seconds have passed."""

    def wrapper(func):
        timers = {}
        lock = threading.Lock()

        @functools.wraps(func)
        def debounced(*args, **kwargs):
            call_args = inspect.getcallargs(func, *args, **kwargs)
            key = call_args[keyed_by] if keyed_by else None

            def run():
                with lock:
                    del timers[key]
                return func(*args, **kwargs)

            with lock:
                old_timer = timers.get(key)
                if old_timer:
                    old_timer.cancel()

                timer = threading.Timer(interval_s, run)
                timers[key] = timer
                timer.start()

        return debounced

    return wrapper


def find_parents(root, path, names):
    """Find files matching the given names relative to the given path.

    Args:
        path (str): The file path to start searching up from.
        names (List[str]): The file/directory names to look for.
        root (str): The directory at which to stop recursing upwards.

    Note:
        The path MUST be within the root.
    """
    if not root:
        return []

    if not os.path.commonprefix((root, path)):
        log.warning("Path %s not in %s", path, root)
        return []

    # Split the relative by directory, generate all the parent directories, then check each of them.
    # This avoids running a loop that has different base-cases for unix/windows
    # e.g. /a/b and /a/b/c/d/e.py -> ['/a/b', 'c', 'd']
    dirs = [root] + os.path.relpath(os.path.dirname(path), root).split(os.path.sep)

    # Search each of /a/b/c, /a/b, /a
    while dirs:
        search_dir = os.path.join(*dirs)
        existing = list(
            filter(os.path.exists, [os.path.join(search_dir, n) for n in names])
        )
        if existing:
            return existing
        dirs.pop()

    # Otherwise nothing
    return []


def match_uri_to_workspace(uri, workspaces):
    if uri is None:
        return None
    max_len, chosen_workspace = -1, None
    path = pathlib.Path(uri).parts
    for workspace in workspaces:
        try:
            workspace_parts = pathlib.Path(workspace).parts
        except TypeError:
            # This can happen in Python2 if 'value' is a subclass of string
            workspace_parts = pathlib.Path(unicode(workspace)).parts
        if len(workspace_parts) > len(path):
            continue
        match_len = 0
        for workspace_part, path_part in zip(workspace_parts, path):
            if workspace_part == path_part:
                match_len += 1
        if match_len > 0:
            if match_len > max_len:
                max_len = match_len
                chosen_workspace = workspace
    return chosen_workspace


def list_to_string(value):
    return ",".join(value) if isinstance(value, list) else value


def merge_dicts(dict_a, dict_b):
    """Recursively merge dictionary b into dictionary a.

    If override_nones is True, then
    """

    def _merge_dicts_(a, b):
        for key in set(a.keys()).union(b.keys()):
            if key in a and key in b:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    yield (key, dict(_merge_dicts_(a[key], b[key])))
                elif b[key] is not None:
                    yield (key, b[key])
                else:
                    yield (key, a[key])
            elif key in a:
                yield (key, a[key])
            elif b[key] is not None:
                yield (key, b[key])

    return dict(_merge_dicts_(dict_a, dict_b))


if sys.platform == "win32":
    import ctypes

    kernel32 = ctypes.windll.kernel32
    PROCESS_SYNCHRONIZE = 0x00100000
    DWORD = ctypes.c_uint32
    BOOL = ctypes.c_int
    LPVOID = ctypes.c_void_p
    HANDLE = LPVOID

    OpenProcess = kernel32.OpenProcess
    OpenProcess.argtypes = [DWORD, BOOL, DWORD]
    OpenProcess.restype = HANDLE

    WaitForSingleObject = kernel32.WaitForSingleObject
    WaitForSingleObject.argtypes = [HANDLE, DWORD]
    WaitForSingleObject.restype = DWORD

    WAIT_TIMEOUT = 0x00000102
    WAIT_ABANDONED = 0x00000080
    WAIT_OBJECT_0 = 0
    WAIT_FAILED = 0xFFFFFFFF

    def is_process_alive(pid):
        """Check whether the process with the given pid is still alive.

        Running `os.kill()` on Windows always exits the process, so it can't be used to check for an alive process.
        see: https://docs.python.org/3/library/os.html?highlight=os%20kill#os.kill

        Hence ctypes is used to check for the process directly via windows API avoiding any other 3rd-party dependency.

        Args:
            pid (int): process ID

        Returns:
            bool: False if the process is not alive or don't have permission to check, True otherwise.
        """
        process = OpenProcess(PROCESS_SYNCHRONIZE, 0, pid)
        if process != 0:
            try:
                wait_result = WaitForSingleObject(process, 0)
                if wait_result == WAIT_TIMEOUT:
                    return True
            finally:
                kernel32.CloseHandle(process)
        return False


else:
    import errno

    def _is_process_alive(pid):
        """Check whether the process with the given pid is still alive.

        Args:
            pid (int): process ID

        Returns:
            bool: False if the process is not alive or don't have permission to check, True otherwise.
        """
        if pid < 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError as e:
            if e.errno == errno.ESRCH:
                return False  # No such process.
            elif e.errno == errno.EPERM:
                return True  # permission denied.
            else:
                log.debug("Unexpected errno: %s", e.errno)
                return False
        else:
            return True

    def is_process_alive(pid):
        from robotframework_ls.subprocess_wrapper import subprocess

        if _is_process_alive(pid):
            # Check if zombie...
            try:
                cmd = ["ps", "-p", str(pid), "-o", "stat"]
                try:
                    process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                except:
                    log.exception("Error calling: %s." % (cmd,))
                else:
                    stdout, _ = process.communicate()
                    stdout = stdout.decode("utf-8", "replace")
                    lines = [line.strip() for line in stdout.splitlines()]
                    if len(lines) > 1:
                        if lines[1].startswith("Z"):
                            return False  # It's a zombie
            except:
                log.exception("Error checking if process is alive.")

            return True
        return False


def _kill_process_and_subprocess_linux(pid):
    from robotframework_ls.subprocess_wrapper import subprocess

    # Ask to stop forking
    subprocess.call(
        ["kill", "-stop", str(pid)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )

    process = subprocess.Popen(
        ["pgrep", "-P", str(pid)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    for pid in process.communicate()[0].splitlines():
        _kill_process_and_subprocess_linux(pid.strip())

    subprocess.call(
        ["kill", "-KILL", str(pid)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )


def kill_process_and_subprocesses(pid):
    from subprocess import CalledProcessError

    if sys.platform == "win32":
        from robotframework_ls.subprocess_wrapper import subprocess

        args = ["taskkill", "/F", "/PID", str(pid), "/T"]
        retcode = subprocess.call(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
        )
        if retcode not in (0, 128, 255):
            raise CalledProcessError(retcode, args)
    else:
        _kill_process_and_subprocess_linux(pid)


_track_pids_to_exit = set()
_watching_thread_global = None


def exit_when_pid_exists(pid):
    _track_pids_to_exit.add(pid)
    global _watching_thread_global
    if _watching_thread_global is None:
        import time

        def watch_parent_process():
            # exit when any of the ids we're tracking exit.
            while True:
                for pid in _track_pids_to_exit:
                    if not is_process_alive(pid):
                        # Note: just exit since the parent process already
                        # exited.
                        log.info("Force-quit process: %s", os.getpid())
                        os._exit(0)

                time.sleep(PARENT_PROCESS_WATCH_INTERVAL)

        _watching_thread_global = threading.Thread(target=watch_parent_process, args=())
        _watching_thread_global.daemon = True
        _watching_thread_global.start()


def overrides(method):
    """
    Meant to be used as
    
    class B:
        @overrides(A.m1)
        def m1(self):
            pass
    """

    @functools.wraps(method)
    def wrapper(func):
        if func.__name__ != method.__name__:
            msg = "Wrong @override: %r expected, but overwriting %r."
            msg = msg % (func.__name__, method.__name__)
            raise AssertionError(msg)

        return func

    return wrapper


def implements(method):
    @functools.wraps(method)
    def wrapper(func):
        if func.__name__ != method.__name__:
            msg = "Wrong @implements: %r expected, but implementing %r."
            msg = msg % (func.__name__, method.__name__)
            raise AssertionError(msg)

        return func

    return wrapper


def log_and_silence_errors(logger, return_on_error=None):
    def inner(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                logger.exception("Error calling: %s", func)
                return return_on_error

        return new_func

    return inner


@contextmanager
def after(obj, method_name, callback):
    original_method = getattr(obj, method_name)

    @functools.wraps(original_method)
    def new_method(*args, **kwargs):
        ret = original_method(*args, **kwargs)
        callback(*args, **kwargs)
        return ret

    setattr(obj, method_name, new_method)
    try:
        yield
    finally:
        setattr(obj, method_name, original_method)


@contextmanager
def before(obj, method_name, callback):
    original_method = getattr(obj, method_name)

    @functools.wraps(original_method)
    def new_method(*args, **kwargs):
        callback(*args, **kwargs)
        ret = original_method(*args, **kwargs)
        return ret

    setattr(obj, method_name, new_method)
    try:
        yield
    finally:
        setattr(obj, method_name, original_method)


def check_min_version(version, min_version):
    """
    :param version:
        This is the version of robotframework.
        
    :param min_version:
        This is the minimum version to match.
        
    :return bool:
        True if version >= min_versiond and False otherwise.
    """
    if version == "N/A":
        return False

    try:
        version = tuple(int(x) for x in version.split("."))
    except:
        return False

    return version >= min_version


def wait_for_condition(condition, msg=None, timeout=DEFAULT_TIMEOUT, sleep=1 / 20.0):
    import time

    curtime = time.time()

    while True:
        if condition():
            break
        if timeout is not None and (time.time() - curtime > timeout):
            error_msg = "Condition not reached in %s seconds" % (timeout,)
            if msg is not None:
                error_msg += "\n"
                if callable(msg):
                    error_msg += msg()
                else:
                    error_msg += str(msg)

            raise TimeoutError(error_msg)
        time.sleep(sleep)
