"""
Helper main which starts the playwright record
"""
import errno
import os
import subprocess
import sys

try:
    import robocorp_code
except ImportError:
    # Automatically add it to the path if __main__ is being executed.
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    import robocorp_code  # @UnusedImport
robocorp_code.import_robocorp_ls_core()


class InstallError(RuntimeError):
    """Error encountered during browser install"""


class RecordingError(RuntimeError):
    """Error encountered during playwright recording"""


def _stdin_write(process, input):
    if input:
        try:
            process.stdin.write(input)
        except BrokenPipeError:
            pass  # communicate() must ignore broken pipe errors.
        except ValueError:
            pass  # communicate() must ignore broken closed pipes
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
    except ValueError:
        pass  # communicate() must ignore broken closed pipes
    except OSError as exc:
        if exc.errno == errno.EINVAL:
            pass
        else:
            raise


def run_playwright_in_thread(launched_event):
    from concurrent.futures import Future
    from threading import Timer

    def mark_run_playwright_as_started():
        launched_event.set()
        print("Playwright recorder started.", flush=True)

    launched_event_timer = Timer(8, mark_run_playwright_as_started)
    future = Future()

    def in_thread():
        from robocorp_code.playwright.robocorp_browser._engines import (
            browsers_path,
        )

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

            # launch event timer -> it will release the lock on the launch event
            launched_event_timer.start()

            # wait for playwright process to finish
            returncode = process.wait()

            if returncode != 0:
                future.set_exception(
                    RecordingError(
                        f"Playwright recorder failed. Output: {''.join(full_output)}"
                    )
                )
                launched_event_timer.cancel()
            else:
                future.set_result(returncode)

        except Exception as e:
            launched_event_timer.cancel()
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
    print("Waiting...", flush=True)
    launched_event.wait()

    if future.exception() is None:
        # Note: This string is being monitored, so, if it's renamed it
        # must also be renamed in `robocorp_code.playwright._Playwright._launch_playwright_recorder`.
        print("Playwright recorder started. If not already triggered.", flush=True)

    # Now, wait for the process to finish (either with the result or exception).
    returncode = future.result()
    print(f"Playwright recorder finished. returncode: {returncode}", flush=True)


def launch() -> None:
    from robocorp_code.playwright.robocorp_browser._engines import (
        BrowserEngine,
        install_browser,
    )

    try:
        launch_playwright()
    except Exception as e:
        print(f"Failed opening recorder:", flush=True)
        # using correct representation as it seems that playwright outputs strange characters
        sys.stdout.buffer.write(f"{e}\n".encode(sys.stdout.encoding, "replace"))
        # attempt to install browsers & drivers
        install_browser(BrowserEngine.CHROME)
        # attempt to launch playwright again
        launch_playwright()


if __name__ == "__main__":
    # Import playwright just to make sure it's in the env (otherwise we can't
    # really do anything).
    import playwright

    print("Opening playwright recorder...", flush=True)
    launch()
