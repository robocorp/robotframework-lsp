import os.path
import sys
from typing import Optional

from robocorp_ls_core.robotframework_log import get_logger


log = get_logger(__name__)


def _import_robotidy():
    try:
        import robotidy
    except ImportError:
        _parent_dir = os.path.dirname(__file__)
        _robotidy_dir = os.path.join(_parent_dir, "libs", "robotidy_lib")
        if not os.path.exists(_robotidy_dir):
            raise RuntimeError("Expected: %s to exist." % (_robotidy_dir,))
        sys.path.append(_robotidy_dir)
        import robotidy  # @UnusedImport

        log.info("Using vendored robotidy")

    log.info("robotidy module: %s", robotidy)


def robot_tidy_source_format(ast, dirname: str) -> Optional[str]:
    _import_robotidy()
    from robotidy.api import transform_model

    transformed_model = transform_model(ast, dirname, ignore_git_dir=True)
    return transformed_model
