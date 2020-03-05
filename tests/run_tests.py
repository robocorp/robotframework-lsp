import sys
import os
import subprocess
import time

if __name__ == "__main__":
    directory = os.path.dirname(os.path.abspath(__file__))
    os.chdir(directory)
    with open("./tests_output.txt", "w") as stream:

        def write(msg):
            for s in (sys.stderr, stream):
                s.write(msg)
                s.write("\n")
                s.flush()

        write("=== Initializing test run ===")
        retcode = 1
        initial_time = time.time()
        try:
            # process = subprocess.Popen(
            #     [sys.executable, "-c", "import sys;print(sys.executable)"],
            #     cwd=directory,
            # )
            process = subprocess.Popen(
                [sys.executable, "-m", "pytest", "-vv", "robotframework_ls_tests"],
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
                        sys.stderr.write("Subprocess leaked: %s (%s)\n" % (s, cmdline))
                        pids.append(s.pid)

                    sys.stderr.flush()

                    from robotframework_ls._utils import kill_process_and_subprocesses

                    kill_process_and_subprocesses(pid)

                sys.exit(1)

            sys.exit(retcode)

        finally:
            write(
                "=== Finalizing test run. Total time: %.2fs ==="
                % (time.time() - initial_time)
            )
