import shutil
from pathlib import Path

from setuptools import find_packages, setup

_here = Path(__file__).parent.resolve()
_parent = _here.parent
_root = _parent.parent

_readme = _here / "README.md"
_thirdparty = _here / "ThirdPartyNotices.txt"
_license = _here / "LICENSE"
_copyright = _here / "COPYRIGHT"

# Note: always overwrite files from the original place if those exist.

_origin = _parent / _readme.name
if _origin.exists():
    shutil.copy2(_origin, _readme)

for path in [_thirdparty, _license, _copyright]:
    _origin = _root / path.name
    if _origin.exists():
        shutil.copy2(_origin, path)


def collect_vendored_files():
    """Provides robot_interactive_console.robot."""
    import os

    VENDORED_ROOT = os.path.dirname(os.path.abspath(__file__))
    VENDORED_ROOT = os.path.join(VENDORED_ROOT, "robotframework_interactive")
    ret = []
    for dir_, _, files in os.walk(VENDORED_ROOT):
        for file_name in files:
            if file_name.lower().endswith((".robot",)):
                rel_dir = os.path.relpath(dir_, VENDORED_ROOT)
                rel_file = os.path.join(rel_dir, file_name)
                ret.append(rel_file)

    assert len(ret) == 1, (
        "Did not collect robot_interactive_console.robot file properly. Found: %s"
        % (ret,)
    )
    return ret


setup(
    name="robotframework-interactive",
    version="0.0.1",
    description="Robot Framework interactive usage (i.e.: an interpreter to be able to interactively use Robot Framework).",
    long_description=_readme.read_text(),
    url="https://github.com/robocorp/robotframework-lsp",
    author="Fabio Zadrozny",
    license="Apache-2.0",
    copyright="Robocorp Technologies, Inc.",
    packages=find_packages(),
    zip_safe=False,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    # List run-time dependencies here. These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=["robotframework >=3.2"],
    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[test]
    extras_require={
        "selenium": ["robotframework-seleniumlibrary >=4.4"],
        "test": [
            "mock",
            "pytest",
            "pytest-regressions==1.0.6",
            "pytest-xdist",
            "pytest-timeout",
        ],
    },
    package_data={"robotframework_interactive": collect_vendored_files()},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Text Editors",
        "Topic :: Text Editors :: Integrated Development Environments (IDE)",
        "Topic :: Software Development :: Debuggers",
        "Framework :: Robot Framework",
        "Framework :: Robot Framework :: Tool",
    ],
)
