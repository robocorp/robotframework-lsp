"""
Helper main which starts the playwright record
"""
import errno
import os
import subprocess
import sys


class InstallError(RuntimeError):
    """Error encountered during browser install"""


class RecordingError(RuntimeError):
    """Error encountered during playwright recording"""


def browsers_path():
    import platform
    from pathlib import Path

    if platform.system() == "Windows":
        return Path.home() / "AppData" / "Local" / "robocorp" / "playwright"
    else:
        return Path.home() / ".robocorp" / "playwright"


def install_browsers(force=False):
    print("Installing browsers...", flush=True)

    cmd = [sys.executable, "-m", "playwright", "install"]
    if force:
        cmd.append("--force")

    env = dict(os.environ)
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path())

    print("Running playwright install...", flush=True)
    result = subprocess.run(
        cmd,
        env=env,
        # Not sure why, but (just when running in VSCode) something as:
        # launching sys.executable actually got stuck unless a \n was written
        # (even if stdin was closed it wasn't enough).
        # -- note: this may be particular to my machine (fabioz), but it
        # may also be related to VSCode + Windows 11 + Windows Defender + python
        input=b"\n",
    )
    print(f"Installation process finished: {result}", flush=True)
    if result.returncode != 0:
        raise InstallError(f"Failed to install drivers.")


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


def run_playwright_in_thread(launched_event):
    from concurrent.futures import Future

    future = Future()

    def in_thread():
        full_output = []
        try:
            target_html = os.path.join(
                os.path.dirname(__file__), "playwright_template.html"
            )

            cmd = [
                sys.executable,
                "-m",
                "playwright",
                "codegen",
                target_html,
            ]
            env = dict(os.environ)
            env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path())
            env["DEBUG"] = "pw:browser"

            process = subprocess.Popen(
                cmd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            # Not sure why, but (just when running in VSCode) something as:
            # launching sys.executable actually got stuck unless a \n was written
            # (even if stdin was closed it wasn't enough).
            # -- note: this may be particular to my machine (fabioz), but it
            # may also be related to VSCode + Windows 11 + Windows Defender + python
            _stdin_write(process, b"\n")

            launched_count = 0
            for line in iter(process.stdout.readline, ""):
                contents = line.decode("utf-8", "replace")
                if not contents:
                    break
                full_output.append(contents)
                if "<launched>" in contents:
                    launched_count += 1
                    if launched_count == 2:
                        # It launches the browser and the 2nd window.
                        launched_event.set()

            returncode = process.wait()

            if returncode != 0:
                future.set_exception(
                    RecordingError(
                        f"Playwright recorder failed. Output: {''.join(full_output)}"
                    )
                )
            else:
                future.set_result(returncode)
        except Exception as e:
            future.set_exception(e)
        finally:
            # If it still wasn't set, set it now.
            launched_event.set()

    import threading

    t = threading.Thread(target=in_thread)
    t.daemon = True
    t.name = "Run Playwright Thread"
    t.start()
    return future


def launch_playwright() -> None:
    import threading

    launched_event = threading.Event()

    future = run_playwright_in_thread(launched_event)

    # Wait for the browser to be launched to print the monitored string ("Playwright recorder started.")
    launched_event.wait()

    # Note: This string is being monitored, so, if it's renamed it
    # must also be renamed in `robocorp_code.playwright._Playwright._launch_playwright_recorder`.
    print("Playwright recorder started.", flush=True)

    # Now, wait for the process to finish (either with the result or exception).
    returncode = future.result()
    print(f"Playwright recorder finished. returcode: {returncode}", flush=True)


def launch() -> None:
    try:
        launch_playwright()
    except Exception as e:
        print(f"Failed opening recorder: {e}", flush=True)
        install_browsers()
        launch_playwright()


if __name__ == "__main__":
    print("Opening playwright recorder...", flush=True)
    launch()
