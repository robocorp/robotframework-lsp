"""
Helper main which starts the playwright record
"""
import os
import sys
import subprocess


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


def install_browsers(force=False, interactive=False):
    print("Installing browsers...")

    cmd = [sys.executable, "-m", "playwright", "install"]
    if force:
        cmd.append("--force")

    env = dict(os.environ)
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path())

    print("Running install...")
    result = subprocess.run(
        cmd,
        capture_output=not interactive,
        start_new_session=not interactive,
        text=True,
        env=env,
    )
    print("Installation process finished:", result)
    if result.returncode != 0:
        if not interactive:
            raise InstallError(f"Failed to install drivers:\n{result.stderr}")
        else:
            raise InstallError(f"Failed to install drivers")


def launch_playwright_recorder():
    # open the playwright recorder
    print("Opening playwright recorder...")

    cmd = [
        sys.executable,
        "-m",
        "playwright",
        "codegen",
        "demo.playwright.dev/todomvc",
    ]
    env = dict(os.environ)
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path())

    result = subprocess.run(
        cmd,
        text=True,
        env=env,
    )

    print("Recording ended:", result)
    if result.returncode != 0:
        raise RecordingError(f"Failed to launch playwright recorder: \n{result.stderr}")
    return result


def launch():
    did_launch_recorder = False
    try:
        launch_playwright_recorder()
        did_launch_recorder = True
    except Exception as e:
        print("Failed opening recorder:", e)
        install_browsers()

    if not did_launch_recorder:
        launch_playwright_recorder()


if __name__ == "__main__":
    launch()
