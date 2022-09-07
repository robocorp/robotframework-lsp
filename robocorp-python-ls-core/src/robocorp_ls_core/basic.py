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
import os
import sys
import threading

from contextlib import contextmanager
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.options import DEFAULT_TIMEOUT
from typing import TypeVar, Any, Callable, Tuple
from robocorp_ls_core.jsonrpc.exceptions import JsonRpcRequestCancelled
from functools import lru_cache


PARENT_PROCESS_WATCH_INTERVAL = 3  # 3 s


def as_str(s) -> str:
    if isinstance(s, bytes):
        return s.decode("utf-8", "replace")
    return str(s)


log = get_logger(__name__)


def list_to_string(value):
    return ",".join(value) if isinstance(value, list) else value


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
                log.info("Unexpected errno: %s", e.errno)
                return False
        else:
            return True

    def is_process_alive(pid):
        from robocorp_ls_core.subprocess_wrapper import subprocess

        if _is_process_alive(pid):
            # Check if zombie...
            try:
                cmd = ["ps", "-p", str(pid), "-o", "stat"]
                try:
                    process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                except:
                    log.exception("Error calling: %s.", " ".join(cmd))
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


def _popen(cmdline, **kwargs):
    import subprocess

    try:
        return subprocess.Popen(cmdline, **kwargs)
    except:
        log.exception("Error running: %s", (" ".join(cmdline)))
        return None


def _call(cmdline, **kwargs):
    import subprocess

    try:
        subprocess.check_call(cmdline, **kwargs)
    except:
        log.exception("Error running: %s", (" ".join(cmdline)))
        return None


def _kill_process_and_subprocess_linux(pid):
    import subprocess

    initial_pid = pid

    def list_children_and_stop_forking(ppid):
        children_pids = []
        _call(
            ["kill", "-STOP", str(ppid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        list_popen = _popen(
            ["pgrep", "-P", str(ppid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if list_popen is not None:
            stdout, _ = list_popen.communicate()
            for line in stdout.splitlines():
                line = line.decode("ascii").strip()
                if line:
                    pid = str(line)
                    children_pids.append(pid)
                    # Recursively get children.
                    children_pids.extend(list_children_and_stop_forking(pid))
        return children_pids

    previously_found = set()

    for _ in range(50):  # Try this at most 50 times before giving up.
        children_pids = list_children_and_stop_forking(initial_pid)
        found_new = False

        for pid in children_pids:
            if pid not in previously_found:
                found_new = True
                previously_found.add(pid)
                _call(
                    ["kill", "-KILL", str(pid)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

        if not found_new:
            break

    # Now, finish the initial one.
    _call(
        ["kill", "-KILL", str(initial_pid)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def kill_process_and_subprocesses(pid):
    log.debug("Killing process and subprocesses of: %s", pid)
    from subprocess import CalledProcessError

    if sys.platform == "win32":
        from robocorp_ls_core.subprocess_wrapper import subprocess

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
                        log.info(
                            f"Force-quit process: %s because parent: %s exited",
                            os.getpid(),
                            pid,
                        )
                        os._exit(0)

                time.sleep(PARENT_PROCESS_WATCH_INTERVAL)

        _watching_thread_global = threading.Thread(target=watch_parent_process, args=())
        _watching_thread_global.daemon = True
        _watching_thread_global.start()


F = TypeVar("F", bound=Callable[..., Any])


def overrides(method: Any) -> Callable[[F], F]:
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
            msg = f"Wrong @override: {func.__name__!r} expected, but overwriting {method.__name__!r}."
            raise AssertionError(msg)

        return func

    return wrapper


def implements(method: Any) -> Callable[[F], F]:
    @functools.wraps(method)
    def wrapper(func):
        if func.__name__ != method.__name__:
            msg = f"Wrong @implements: {func.__name__!r} expected, but implementing {method.__name__!r}."
            raise AssertionError(msg)

        return func

    return wrapper


def log_and_silence_errors(logger, return_on_error=None):
    def inner(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except JsonRpcRequestCancelled:
                logger.info("Cancelled handling: %s", func)
                raise  # Don't silence cancelled exceptions
            except:
                logger.exception("Error calling: %s", func)
                return return_on_error

        return new_func

    return inner


def log_but_dont_silence_errors(logger):
    def inner(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except JsonRpcRequestCancelled:
                logger.info("Cancelled handling: %s", func)
                raise  # Don't silence cancelled exceptions
            except:
                logger.exception("Error calling: %s", func)
                raise

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


def check_min_version(version: str, min_version: Tuple[int, int]) -> bool:
    """
    :param version:
        This is the version of robotframework.

    :param min_version:
        This is the minimum version to match.

    :return bool:
        True if version >= min_versiond and False otherwise.
    """
    try:
        v = tuple(int(x) for x in version.split("."))
    except:
        return False

    return v >= min_version


def wait_for_condition(condition, msg=None, timeout=DEFAULT_TIMEOUT, sleep=1 / 20.0):
    """
    Note: wait_for_expected_func_return is usually a better API to use as
    the error message is automatically built.
    """
    import time

    curtime = time.time()

    while True:
        if condition():
            break
        if timeout is not None and (time.time() - curtime > timeout):
            error_msg = f"Condition not reached in {timeout} seconds"
            if msg is not None:
                error_msg += "\n"
                if callable(msg):
                    error_msg += msg()
                else:
                    error_msg += str(msg)

            raise TimeoutError(error_msg)
        time.sleep(sleep)


def wait_for_non_error_condition(
    generate_error_or_none, timeout=DEFAULT_TIMEOUT, sleep=1 / 20.0
):
    import time

    curtime = time.time()

    while True:
        error_msg = generate_error_or_none()
        if error_msg is None:
            break

        if timeout is not None and (time.time() - curtime > timeout):
            raise TimeoutError(
                f"Condition not reached in {timeout} seconds\n{error_msg}"
            )
        time.sleep(sleep)


def wait_for_expected_func_return(
    func, expected_return, timeout=DEFAULT_TIMEOUT, sleep=1 / 20.0
):
    def check():
        found = func()
        if found != expected_return:
            return "Expected: %s. Found: %s" % (expected_return, found)

        return None

    wait_for_non_error_condition(check, timeout, sleep)


def isinstance_name(obj, classname, memo={}):
    """
    Checks if a given object is instance of a class with the given name.
    """
    if classname.__class__ in (list, tuple):
        for c in classname:
            if isinstance_name(obj, c):
                return True
        return False

    cls = obj.__class__
    key = (cls, classname)
    try:
        return memo[key]
    except KeyError:
        if cls.__name__ == classname:
            memo[key] = True
        else:
            for check in obj.__class__.__mro__:
                if check.__name__ == classname:
                    memo[key] = True
                    break
            else:
                memo[key] = False

        return memo[key]


def build_subprocess_kwargs(cwd, env, **kwargs) -> dict:
    from robocorp_ls_core.subprocess_wrapper import subprocess

    startupinfo = None
    if sys.platform == "win32":
        # We don't want to show the shell on windows!
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        startupinfo = startupinfo

    if cwd:
        kwargs["cwd"] = cwd
    if env:
        kwargs["env"] = env
    kwargs["startupinfo"] = startupinfo
    return kwargs


def make_unique(lst):
    seen = set()
    return [x for x in lst if x not in seen and not seen.add(x)]


@lru_cache(maxsize=3000)
def normalize_filename(filename):
    return os.path.abspath(os.path.normpath(os.path.normcase(filename)))


class _RestoreCtxManager(object):
    def __init__(self, original_import):
        self._original_import = original_import

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        import builtins

        builtins.__import__ = self._original_import


def notify_about_import(import_name):
    """
    :param str import_name:
        The name of the import we don't want in this process.

    Use case: `robot` should not be imported in the Robot Framework Language
    Server process. It should only be imported in the subprocess which is
    spawned specifically for that robot framework version (we should only parse
    the AST at those subprocesses -- if the import is done at the main process
    something needs to be re-engineered to forward the request to a subprocess).

    If used as a context manager restores the previous __import__.
    """
    import builtins

    original_import = builtins.__import__

    import_name_with_dot = import_name + "."

    def new_import(name, *args, **kwargs):
        if name == import_name or name.startswith(import_name_with_dot):
            from io import StringIO
            import traceback

            stream = StringIO()
            stream.write(f"'{name}' should not be imported in this process.\nStack:\n")

            traceback.print_stack(file=stream)

            log.critical(stream.getvalue())

        return original_import(name, *args, **kwargs)

    builtins.__import__ = new_import
    return _RestoreCtxManager(original_import)
