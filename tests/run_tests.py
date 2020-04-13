import sys
import os
import subprocess
import time
from contextlib import contextmanager

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]


@contextmanager
def _noop_ctx():
    yield None


def main():
    args = sys.argv[1:]
    if len(args) >= 1:
        if len(args) != 1:
            raise AssertionError(
                "Expected at most 1 argument. Found: %s (%s)" % (len(args), args)
            )
        test_output_filename = args[0]
        open_stream = lambda: open(
            os.path.join(os.path.dirname(__file__), test_output_filename), "w"
        )
    else:
        # Without arguments runs without logging to any file.
        open_stream = _noop_ctx

    with open_stream() as stream:

        def write(msg):
            for s in (sys.stderr, stream):
                if s is not None:
                    s.write(msg)
                    s.write("\n")
                    s.flush()

        write("=== Initializing test run ===")
        retcode = 1
        initial_time = time.time()
        try:
            directory = os.path.dirname(os.path.abspath(__file__))
            os.chdir(directory)
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-vv",
                    "robotframework_ls_tests",
                    "robotframework_debug_adapter_tests",
                ],
                cwd=directory,
            )
            pid = process.pid
            TIMEOUT = 100
            while (time.time() - initial_time) < TIMEOUT:
                time.sleep(1)
                process_retcode = process.poll()
                if process_retcode is not None:
                    retcode = process_retcode
                    process = None
                    break
            else:
                write(
                    "Running tests timed out (pid: %s, timeout: %s seconds)."
                    % (pid, TIMEOUT)
                )
                try:
                    import psutil
                except ImportError:
                    pass
                else:
                    pids = []
                    p = psutil.Process()
                    for s in p.children(recursive=True):
                        try:
                            cmdline = s.cmdline()
                        except Exception as e:
                            cmdline = str(e)
                        write("Subprocess leaked: %s (%s)\n" % (s, cmdline))
                        pids.append(s.pid)

                    from robotframework_ls._utils import kill_process_and_subprocesses

                    kill_process_and_subprocesses(pid)

                sys.exit(1)

            sys.exit(retcode)

        finally:
            write(
                "=== Finalizing test run. Total time: %.2fs ==="
                % (time.time() - initial_time)
            )


if __name__ == "__main__":
    main()
