import os
import subprocess
import sys
import threading
import time
from typing import Any, Generic, List, Optional, TypeVar, Union

# Hack so that we don't break the runtime on versions prior to Python 3.8.
if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass

    class TypedDict(object):
        def __init_subclass__(self, *args, **kwargs):
            pass

else:
    from typing import TypedDict

from robocorp_ls_core.constants import NULL
from robocorp_ls_core.protocols import IProgressReporter, Sentinel
from robocorp_ls_core.robotframework_log import get_log_level, get_logger
import errno

log = get_logger(__name__)

T = TypeVar("T")


class LaunchActionResultDict(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Any


class LaunchActionResult(Generic[T]):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[T]

    # A string-representation of the command line.
    command_line: str

    def __init__(
        self,
        command_line: str,
        success: bool,
        message: Optional[str] = None,
        result: Optional[T] = None,
    ):
        self.success = success
        self.message = message
        self.result = result
        self.command_line = command_line

    def as_dict(self) -> LaunchActionResultDict:
        return {"success": self.success, "message": self.message, "result": self.result}

    def __str__(self):
        return f"LaunchActionResult(success={self.success!r}, message={self.message!r}, result={self.result!r})"

    __repr__ = __str__


def launch(
    args: Union[List[str], str],
    timeout: float = 35,
    error_msg: str = "",
    mutex_name=None,
    cwd: Optional[str] = None,
    log_errors=True,
    stderr=Sentinel.SENTINEL,
    show_interactive_output: bool = False,
    hide_in_log: Optional[str] = None,
    env: Optional[dict] = None,
    **kwargs,
) -> LaunchActionResult:
    """
    Returns an LaunchActionResult where the result is the stdout of the executed command.

    :param log_errors:
        If false, errors won't be logged (i.e.: should be false when errors
        are expected).

    :param stderr:
        If given sets the stderr redirection (by default it's subprocess.PIPE,
        but users could change it to something as subprocess.STDOUT).

    :param hide_in_log:
        A string which should be hidden in logs.
    """
    from robocorp_ls_core.basic import build_subprocess_kwargs
    from subprocess import (
        CalledProcessError,
        TimeoutExpired,
        list2cmdline,
        check_output,
    )
    from robocorp_ls_core.basic import as_str

    if stderr is Sentinel.SENTINEL:
        stderr = subprocess.PIPE

    new_env = os.environ.copy()
    new_env.pop("PYTHONPATH", "")
    new_env.pop("PYTHONHOME", "")
    new_env.pop("VIRTUAL_ENV", "")
    new_env["PYTHONIOENCODING"] = "utf-8"
    new_env["PYTHONUNBUFFERED"] = "1"

    if env:
        new_env.update(env)

    suprocesskwargs: dict = build_subprocess_kwargs(
        cwd, new_env, stderr=stderr, **kwargs
    )
    cmdline: str
    if isinstance(args, str):
        # When shell=True args should be a string.
        cmdline = args
    else:
        cmdline = list2cmdline([str(x) for x in args])

    try:
        if mutex_name:
            from robocorp_ls_core.system_mutex import timed_acquire_mutex
        else:
            timed_acquire_mutex = NULL
        with timed_acquire_mutex(mutex_name, timeout=15):
            if get_log_level() >= 2:
                msg = f"Running: {cmdline}"
                if hide_in_log:
                    msg = msg.replace(hide_in_log, "<HIDDEN_IN_LOG>")

                log.debug(msg)

            curtime = time.time()

            boutput: bytes
            # We have 2 main modes here: one in which we can print the output
            # interactively while the command is running and another where
            # we only print if some error happened.
            if not show_interactive_output:
                # Not sure why, but (just when running in VSCode) something as:
                # launching sys.executable actually got stuck unless a \n was written
                # (even if stdin was closed it wasn't enough).
                # -- note: this may be particular to my machine (fabioz), but it
                # may also be related to VSCode + Windows 11 + Windows Defender + python
                suprocesskwargs["input"] = b"\n"
                boutput = check_output(args, timeout=timeout, **suprocesskwargs)
            else:
                from robocorp_ls_core.progress_report import (
                    get_current_progress_reporter,
                )

                progress_reporter = get_current_progress_reporter()

                def on_output(content):
                    try:
                        sys.stderr.buffer.write(content)

                        # Besides writing it to stderr, let's also add more
                        # info to our current progress (if any).
                        if progress_reporter is not None:
                            progress_reporter.set_additional_info(
                                content.decode("utf-8", "replace")
                            )
                    except Exception:
                        log.exception("Error reporting interactive output.")

                boutput = check_output_interactive(
                    args,
                    timeout=timeout,
                    on_stderr=on_output,
                    on_stdout=on_output,
                    progress_reporter=progress_reporter,
                    **suprocesskwargs,
                )

    except CalledProcessError as e:
        stdout = as_str(e.stdout)
        stderr = as_str(e.stderr)
        msg = f"Error running: {cmdline}.\n\nStdout: {stdout}\nStderr: {stderr}"
        if hide_in_log:
            msg = msg.replace(hide_in_log, "<HIDDEN_IN_LOG>")

        if log_errors:
            log.exception(msg)
        if not error_msg:
            return LaunchActionResult(cmdline, success=False, message=msg)
        else:
            additional_info = [error_msg]
            if stdout or stderr:
                if stdout and stderr:
                    additional_info.append("\nDetails: ")
                    additional_info.append("\nStdout")
                    additional_info.append(stdout)
                    additional_info.append("\nStderr")
                    additional_info.append(stderr)

                elif stdout:
                    additional_info.append("\nDetails: ")
                    additional_info.append(stdout)

                elif stderr:
                    additional_info.append("\nDetails: ")
                    additional_info.append(stderr)

            return LaunchActionResult(
                cmdline, success=False, message="".join(additional_info)
            )

    except TimeoutExpired:
        msg = f"Timed out ({timeout}s elapsed) when running: {cmdline}"
        log.exception(msg)
        return LaunchActionResult(cmdline, success=False, message=msg)

    except Exception:
        msg = f"Error running: {cmdline}"
        log.exception(msg)
        return LaunchActionResult(cmdline, success=False, message=msg)

    output = boutput.decode("utf-8", "replace")

    do_log_as_info = not show_interactive_output and (
        (log_errors and get_log_level() >= 1) or get_log_level() >= 2
    )
    if do_log_as_info:
        elapsed = time.time() - curtime
        msg = f"Output from: {cmdline} (took: {elapsed:.2f}s): {output}"
        if hide_in_log:
            msg = msg.replace(hide_in_log, "<HIDDEN_IN_LOG>")
        log.info(msg)

    return LaunchActionResult(cmdline, success=True, message=None, result=output)


def check_output_interactive(
    *popenargs,
    timeout=None,
    progress_reporter: Optional[IProgressReporter] = None,
    **kwargs,
) -> bytes:
    """
    This has the same API as subprocess.check_output, but allows us to work with
    the contents being generated by the subprocess before the subprocess actually
    finishes.

    :param on_stderr:
        A callable(string) (called from another thread) whenever output is
        written with stderr contents.

    :param on_stdout:
        A callable(string) (called from another thread) whenever output is
        written with stdout contents.

    :return: the stdout generated by the command.
    """
    from robocorp_ls_core.basic import kill_process_and_subprocesses

    if kwargs.get("stdout", subprocess.PIPE) != subprocess.PIPE:
        raise AssertionError("stdout must be subprocess.PIPE")

    if kwargs.get("stderr", subprocess.PIPE) != subprocess.PIPE:
        # We could potentially also accept `subprocess.STDOUT`, but let's leave
        # this as a future improvement for now.
        raise AssertionError("stderr must be subprocess.PIPE")

    kwargs["stdout"] = subprocess.PIPE
    kwargs["stderr"] = subprocess.PIPE
    kwargs["stdin"] = subprocess.PIPE

    on_stderr = kwargs.pop("on_stderr")
    on_stdout = kwargs.pop("on_stdout")
    stdout_contents: List[bytes] = []
    stderr_contents: List[bytes] = []

    def stream_reader(stream, callback, contents_list: List[bytes]):
        for line in iter(stream.readline, b""):
            if not line:
                break
            contents_list.append(line)
            callback(line)

    def check_progress_cancelled(process, progress_reporter: IProgressReporter):
        try:
            while process.poll() is None:
                try:
                    process.wait(1)
                except:
                    if progress_reporter.cancelled:
                        retcode = process.poll()
                        if retcode is None:
                            msg_str = f"Progress was cancelled (Process pid: {process.pid} was killed).\n"
                            msg = msg_str.encode("utf-8")
                            log.info(msg_str)
                            stderr_contents.insert(0, msg)
                            stderr_contents.append(msg)
                            on_stderr(msg)
                            kill_process_and_subprocesses(process.pid)
        except:
            log.exception("Error checking that progress was cancelled.")

    with subprocess.Popen(*popenargs, **kwargs) as process:
        threads = [
            threading.Thread(
                target=stream_reader,
                args=(process.stdout, on_stdout, stdout_contents),
                name="stream_reader_stdout",
            ),
            threading.Thread(
                target=stream_reader,
                args=(process.stderr, on_stderr, stderr_contents),
                name="stream_reader_stderr",
            ),
        ]
        if progress_reporter is not None:
            t = threading.Thread(
                target=check_progress_cancelled,
                args=(process, progress_reporter),
                name="check_progress_cancelled",
            )
            t.start()

        if process.stdin:
            # Not sure why, but (just when running in VSCode) something as:
            # launching sys.executable actually got stuck unless a \n was written
            # (even if stdin was closed it wasn't enough).
            # -- note: this may be particular to my machine (fabioz), but it
            # may also be related to VSCode + Windows 11 + Windows Defender + python
            _stdin_write(process, b"\n")

        for t in threads:
            t.start()

        retcode: Optional[int]
        try:
            try:
                retcode = process.wait(timeout)
            except:
                # i.e.: KeyboardInterrupt / TimeoutExpired
                retcode = process.poll()

                if retcode is None:
                    # It still hasn't completed: kill it.
                    try:
                        kill_process_and_subprocesses(process.pid)
                    except:
                        log.exception("Error killing pid: %s" % (process.pid,))

                    retcode = process.wait()
                raise

        finally:
            for t in threads:
                t.join()

        if retcode:
            raise subprocess.CalledProcessError(
                retcode,
                process.args,
                output=b"".join(stdout_contents),
                stderr=b"".join(stderr_contents),
            )

        return b"".join(stdout_contents)


def _stdin_write(process, input):
    if input:
        try:
            process.stdin.write(input)
        except BrokenPipeError:
            pass  # communicate() must ignore broken pipe errors.
        except OSError as exc:
            if exc.errno == errno.EINVAL:
                # bpo-19612, bpo-30418: On Windows, stdin.write() fails
                # with EINVAL if the child process exited or if the child
                # process is still running but closed the pipe.
                pass
            else:
                raise

    try:
        process.stdin.close()
    except BrokenPipeError:
        pass  # communicate() must ignore broken pipe errors.
    except OSError as exc:
        if exc.errno == errno.EINVAL:
            pass
        else:
            raise
