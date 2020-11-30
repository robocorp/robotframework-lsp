"""
This is a script to help with the automation of common development tasks.

It requires 'fire' to be installed for the command line automation (i.e.: pip install fire).

Some example commands:

    python -m dev set-version 0.0.2
    python -m dev check-tag-version
    python -m dev vendor-robocorp-ls-core
"""
import sys
import os
import traceback

__file__ = os.path.abspath(__file__)

if not os.path.exists(os.path.join(os.path.abspath("."), "dev.py")):
    raise RuntimeError('Please execute commands from the directory containing "dev.py"')


try:
    import robocorp_code
except ImportError:
    # I.e.: add relative path (the cwd must be the directory containing this file).
    sys.path.append("src")
    import robocorp_code

robocorp_code.import_robocorp_ls_core()


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
            version, os.path.join(".", "src", "robocorp_code", "__init__.py")
        )

    def get_tag(self):
        import subprocess

        # i.e.: Gets the last tagged version
        cmd = "git describe --tags --abbrev=0 --match robocorp-code*".split()
        popen = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, stderr = popen.communicate()

        # Something as: b'robocorp-code-0.0.1'
        stdout = stdout.decode("utf-8")
        stdout = stdout.strip()
        return stdout

    def check_tag_version(self):
        """
        Checks if the current tag matches the latest version (exits with 1 if it
        does not match and with 0 if it does match).
        """
        import subprocess

        version = self.get_tag()
        version = version[version.rfind("-") + 1 :]

        if robocorp_code.__version__ == version:
            sys.stderr.write("Version matches (%s) (exit(0))\n" % (version,))
            sys.exit(0)
        else:
            sys.stderr.write(
                "Version does not match (found in sources: %s != tag: %s) (exit(1))\n"
                % (robocorp_code.__version__, version)
            )
            sys.exit(1)

    def remove_vendor_robocorp_ls_core(self):
        import time
        import shutil

        vendored_dir = os.path.join(
            os.path.dirname(__file__),
            "src",
            "robocorp_code",
            "vendored",
            "robocorp_ls_core",
        )
        try:
            shutil.rmtree(vendored_dir)
            time.sleep(0.5)
        except:
            if os.path.exists(vendored_dir):
                traceback.print_exc()
        return vendored_dir

    def vendor_robocorp_ls_core(self):
        """
        Vendors robocorp_ls_core into robocorp_code/vendored.
        """
        import shutil

        src_core = os.path.join(
            os.path.dirname(__file__),
            "..",
            "robocorp-python-ls-core",
            "src",
            "robocorp_ls_core",
        )
        vendored_dir = self.remove_vendor_robocorp_ls_core()
        print("Copying from: %s to %s" % (src_core, vendored_dir))

        shutil.copytree(src_core, vendored_dir)
        print("Finished vendoring.")

    def codegen(self):
        """
        Generates code (to add actions, settings, etc).
        In particular, generates the package.json and auxiliary files with
        constants in the code.
        """

        try:
            import codegen_package
        except ImportError:
            # I.e.: add relative path (the cwd must be the directory containing this file).
            sys.path.append("codegen")
            import codegen_package
        codegen_package.main()

    def fix_readme(self):
        """
        Updates the links in the README.md to match the current tagged version.
        To be called during release.
        """
        import re

        readme = os.path.join(os.path.dirname(__file__), "README.md")
        with open(readme, "r") as f:
            content = f.read()

        tag = self.get_tag()

        new_content = re.sub(
            r"\(docs/",
            fr"(https://github.com/robocorp/robotframework-lsp/tree/{tag}/robocorp-code/docs/",
            content,
        )

        new_content = re.sub(
            r"\(images/",
            fr"(https://raw.githubusercontent.com/robocorp/robotframework-lsp/{tag}/robocorp-code/images/",
            content,
        )

        new_content = new_content.replace(
            "Apache 2.0",
            "[Robocorp License Agreement (pdf)](https://cdn.robocorp.com/legal/Robocorp-EULA-v1.0.pdf)",
        )

        assert "apache" not in new_content.lower()
        with open(readme, "w") as f:
            f.write(new_content)

    def generate_license_file(self):
        import tempfile
        import subprocess
        import time
        from robocorp_code.rcc import download_rcc

        rcc_location = os.path.join(tempfile.mkdtemp(), "rcc.exe")
        download_rcc(rcc_location)
        time.sleep(0.2)
        print(f"Downloaded rcc to: {rcc_location}")
        assert os.path.exists(rcc_location)

        readme = os.path.join(os.path.dirname(__file__), "LICENSE.txt")
        with open(readme, "w") as f:
            output = subprocess.check_output([rcc_location, "man", "eula"])
            f.write(output.decode("utf-8"))

    def local_install(self):
        """
        Packages both Robotframework Language Server and Robocorp Code and installs
        them in Visual Studio Code.
        """
        import subprocess

        print("Making local install")
        from pathlib import Path

        root = Path(__file__).parent.parent

        def run(args, shell=False):
            print("---", " ".join(args))
            return subprocess.check_call(args, cwd=curdir, shell=shell)

        def get_version():
            import json

            p = Path(curdir / "package.json")
            contents = json.loads(p.read_text())
            return contents["version"]

        print("--- installing RobotFramework Language Server")
        curdir = root / "robotframework-ls"
        run("python -m dev vendor_robocorp_ls_core".split())
        run("vsce package".split(), shell=True)
        run(
            f"code --install-extension robotframework-lsp-{get_version()}.vsix".split(),
            shell=True,
        )
        run("python -m dev remove_vendor_robocorp_ls_core".split())

        print("\n--- installing Robocorp Code")
        curdir = root / "robocorp-code"
        run("python -m dev vendor_robocorp_ls_core".split())
        run("vsce package".split(), shell=True)
        run(
            f"code --install-extension robocorp-code-{get_version()}.vsix".split(),
            shell=True,
        )
        run("python -m dev remove_vendor_robocorp_ls_core".split())


def test_lines():
    """
    Check that the replace matches what we expect.

    Things we must match:

        version="0.0.1"
        "version": "0.0.1",
        __version__ = "0.0.1"
    """
    from robocorp_ls_core.unittest_tools.compare import compare_lines

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

        try:
            import fire
        except ImportError:
            sys.stderr.write(
                '\nError. "fire" library not found.\nPlease install with "pip install fire" (or activate the proper env).\n'
            )
        else:
            # Workaround so that fire always prints the output.
            # See: https://github.com/google/python-fire/issues/188
            def Display(lines, out):
                text = "\n".join(lines) + "\n"
                out.write(text)

            from fire import core

            core.Display = Display

            fire.Fire(Dev())
