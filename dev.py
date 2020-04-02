"""
This is a script to help with the automation of common development tasks.

It requires 'fire' to be installed for the command line automation (i.e.: pip install fire).

Some example commands:

    python -m dev set-version 0.0.2
    python -m dev check-tag-version
"""
import sys
import os

__file__ = os.path.abspath(__file__)

if not os.path.exists(os.path.join(os.path.abspath("."), "dev.py")):
    raise RuntimeError('Please execute commands from the directory containing "dev.py"')

import fire

try:
    import devtools
except ImportError:
    # I.e.: add relative path (the cwd must be the directory containing this file).
    sys.path.append("devtools_src")
    import devtools

try:
    import robotframework_ls
except ImportError:
    # I.e.: add relative path (the cwd must be the directory containing this file).
    sys.path.append("src")
    import robotframework_ls


class Dev(object):
    def set_version(self, version):
        """
        Sets a new version for robotframework-lsp in all the needed files.
        """
        from devtools import update_version

        update_version.update_version(version, os.path.join(".", "package.json"))
        update_version.update_version(version, os.path.join(".", "src", "setup.py"))
        update_version.update_version(
            version, os.path.join(".", "src", "robotframework_ls", "__init__.py")
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

        if robotframework_ls.__version__ == version:
            sys.stderr.write("Version matches (%s) (exit(0))\n" % (version,))
            sys.exit(0)
        else:
            sys.stderr.write(
                "Version does not match (lsp: %s != tag: %s) (exit(1))\n"
                % (robotframework_ls.__version__, version)
            )
            sys.exit(1)


if __name__ == "__main__":
    fire.Fire(Dev())
