"""
This is a script to help with the automation of common development tasks.

It requires 'fire' to be installed for the command line automation (i.e.: pip install fire).

Some example commands:

    python -m dev set-version 0.0.2
    python -m dev check-tag-version
    python -m dev vendor-robocode-ls-core
"""
import sys
import os

__file__ = os.path.abspath(__file__)

if not os.path.exists(os.path.join(os.path.abspath("."), "dev.py")):
    raise RuntimeError('Please execute commands from the directory containing "dev.py"')

import fire

try:
    import robocode_vscode
except ImportError:
    # I.e.: add relative path (the cwd must be the directory containing this file).
    sys.path.append("src")
    import robocode_vscode

robocode_vscode.import_robocode_ls_core()


def _fix_contents_version(contents, version):
    import re

    contents = re.sub(
        r"(version\s*=\s*)\"\d+\.\d+\.\d+", r'\1"%s' % (version,), contents
    )
    contents = re.sub(
        r"(__version__\s*=\s*)\"\d+\.\d+\.\d+", r'\1"%s' % (version,), contents
    )
    contents = re.sub(
        r"(\"version\"\s*:\s*)\"\d+\.\d+\.\d+", r'\1"%s' % (version,), contents
    )

    return contents


class Dev(object):

    def set_version(self, version):
        """
        Sets a new version for robotframework-lsp in all the needed files.
        """

        def update_version(version, filepath):
            with open(filepath, "r") as stream:
                contents = stream.read()

            new_contents = _fix_contents_version(contents, version)
            if contents != new_contents:
                with open(filepath, "w") as stream:
                    stream.write(new_contents)

        update_version(version, os.path.join(".", "package.json"))
        update_version(version, os.path.join(".", "src", "setup.py"))
        update_version(
            version, os.path.join(".", "src", "robocode_vscode", "__init__.py")
        )

    def check_tag_version(self):
        """
        Checks if the current tag matches the latest version (exits with 1 if it
        does not match and with 0 if it does match).
        """
        import subprocess

        # i.e.: Gets the last tagged version
        cmd = "git describe --tags --abbrev=0".split()
        popen = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, stderr = popen.communicate()

        # Something as: b'robotframework-lsp-0.0.1'
        if sys.version_info[0] >= 3:
            stdout = stdout.decode("utf-8")

        version = stdout.strip()
        version = version[version.rfind("-") + 1 :]

        if robocode_vscode.__version__ == version:
            sys.stderr.write("Version matches (%s) (exit(0))\n" % (version,))
            sys.exit(0)
        else:
            sys.stderr.write(
                "Version does not match (found in sources: %s != tag: %s) (exit(1))\n"
                % (robocode_vscode.__version__, version)
            )
            sys.exit(1)

    def vendor_robocode_ls_core(self):
        """
        Vendors robocode_ls_core into robocode_vscode/vendored.
        """
        import shutil

        src_core = os.path.join(
            os.path.dirname(__file__),
            "..",
            "robocode-python-ls-core",
            "src",
            "robocode_ls_core",
        )
        vendored_dir = os.path.join(
            os.path.dirname(__file__),
            "src",
            "robocode_vscode",
            "vendored",
            "robocode_ls_core",
        )
        print("Copying from: %s to %s" % (src_core, vendored_dir))
        shutil.copytree(src_core, vendored_dir)
        print("Finished vendoring.")


def test_lines():
    """
    Check that the replace matches what we expect.

    Things we must match:

        version="0.0.1"
        "version": "0.0.1",
        __version__ = "0.0.1"
    """
    from robocode_ls_core.unittest_tools.compare import compare_lines

    contents = _fix_contents_version(
        """
        version="0.0.198"
        version = "0.0.1"
        "version": "0.0.1",
        "version":"0.0.1",
        "version" :"0.0.1",
        __version__ = "0.0.1"
        """,
        "3.7.1",
    )

    expected = """
        version="3.7.1"
        version = "3.7.1"
        "version": "3.7.1",
        "version":"3.7.1",
        "version" :"3.7.1",
        __version__ = "3.7.1"
        """

    compare_lines(contents.splitlines(), expected.splitlines())


if __name__ == "__main__":
    TEST = False
    if TEST:
        test_lines()
    else:

        # Workaround so that fire always prints the output.
        # See: https://github.com/google/python-fire/issues/188
        def Display(lines, out):
            text = "\n".join(lines) + "\n"
            out.write(text)

        from fire import core

        core.Display = Display

        fire.Fire(Dev())
