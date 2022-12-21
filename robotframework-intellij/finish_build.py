"""
Script that'll add the Python contents of robotframework-lsp to
the intellij distribution.
"""

import os.path
import sys
from pathlib import Path

curdir = os.path.abspath(os.path.dirname(__file__))


def main():
    import zipfile

    try:
        from robotframework_ls import __version__
    except ImportError:
        p = Path(os.path.dirname(curdir)) / "robotframework-ls" / "src"
        assert p.exists()
        sys.path.append(str(p))
        from robotframework_ls import __version__

    wheel_file = os.path.join(
        os.path.dirname(curdir),
        f"robotframework-ls/src/dist/robotframework_lsp-{__version__}-py2.py3-none-any.whl",
    )

    target = (
        Path(curdir)
        / "build"
        / "distributions"
        / f"robotframework-intellij-{__version__}.zip"
    )
    assert target.exists()
    with zipfile.ZipFile(target, "a", zipfile.ZIP_DEFLATED) as target_z:

        assert os.path.exists(wheel_file), "%s does not exist." % (wheel_file,)
        with zipfile.ZipFile(wheel_file, "r") as z:
            for name in z.namelist():
                with z.open(name, "r") as stream:
                    contents = stream.read()
                    assert isinstance(contents, bytes)

                    target_z.writestr("robotframework-intellij/lib/" + name, contents)


if __name__ == "__main__":
    main()
