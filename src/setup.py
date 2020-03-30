from setuptools import find_packages, setup
import os

_dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_readme_filename = os.path.join(_dirname, "README.md")
if not os.path.exists(_readme_filename):
    raise AssertionError("Expected: %s to exist." % (_readme_filename,))
README = open(_readme_filename, "r").read()

setup(
    name="robotframework-ls",
    version="0.0.5",
    description="VSCode extension support for Robot Framework",
    long_description=README,
    url="https://github.com/robocorp/robotframework-lsp",
    author="Fabio Zadrozny",
    copyright="Robocorp Technologies, Inc.",
    packages=find_packages(exclude=["robotframework_ls_tests"]),
    # List run-time dependencies here. These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[],
    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[test]
    extras_require={
        "test": [
            "mock",
            "pytest",
            "pytest-regressions==1.0.6",
            "pytest-xdist",
            "pytest-timeout",
        ]
    },
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        "console_scripts": ["robotframework_ls = robotframework_ls.__main__:main"],
        "jupyter_lsp_spec_v1": [
            "robotframework_ls = robotframework_ls.ext.jupyter_lsp:spec_v1"
        ],
    },
)
