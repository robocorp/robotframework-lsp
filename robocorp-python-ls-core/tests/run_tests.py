"""
Helper to run pytests with a timeout and output the output to a file.

The default timeout is 100 seconds and it can be customized
with a 'RUN_TESTS_TIMEOUT' environment variable.
"""

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

    # If -o is not passed, without logging to any file. All other arguments
    # are passed on to pytest.
    open_stream = _noop_ctx
    pytest_args = []
    for arg in args:
        if arg.startswith("-o"):
            test_output_filename = arg[2:]
            open_stream = lambda: open(test_output_filename, "w")
        else:
            pytest_args.append(arg)

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
            args = [sys.executable, "-m", "pytest"] + pytest_args
            timeout = int(os.environ.get("RUN_TESTS_TIMEOUT", "100"))
            write(
                "Calling:\n  cwd:%s\n  args: %s\n  timeout: %s"
                % (os.path.abspath(os.getcwd()), args, timeout)
            )
            process = subprocess.Popen(args)
            pid = process.pid
            while (time.time() - initial_time) < timeout:
                time.sleep(1)
                process_retcode = process.poll()
                if process_retcode is not None:
                    retcode = process_retcode
                    process = None
                    break
            else:
                write(
                    "Running tests timed out (pid: %s, timeout: %s seconds)."
                    % (pid, timeout)
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

                    try:
                        from robocorp_ls_core.basic import kill_process_and_subprocesses
                    except:
                        # Automatically add it to the path if not there.
                        sys.path.append(
                            os.path.join(
                                os.path.dirname(
                                    os.path.dirname(os.path.abspath(__file__))
                                ),
                                "src",
                            )
                        )
                        from robocorp_ls_core.basic import kill_process_and_subprocesses

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
