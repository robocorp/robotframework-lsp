import os.path
from pathlib import Path
import sys
from typing import List, Dict

from robocorp_ls_core.robotframework_log import get_logger


log = get_logger(__name__)


def _import_robocop():
    try:
        import robocop
    except ImportError:
        _parent_dir = os.path.dirname(__file__)
        _robocop_dir = os.path.join(_parent_dir, "libs", "robocop_lib")
        if not os.path.exists(_robocop_dir):
            raise RuntimeError("Expected: %s to exist." % (_robocop_dir,))
        sys.path.append(_robocop_dir)
        import robocop  # @UnusedImport

        log.info("Using vendored Robocop")

    log.info("Robocop module: %s", robocop)


def collect_robocop_diagnostics(
    project_root: Path, ast_model, filename: str, source: str
) -> List[Dict]:

    _import_robocop()

    import robocop
    from robocop.config import Config
    from robocop.utils import issues_to_lsp_diagnostic

    filename_parent = Path(filename).parent
    if filename_parent.exists():
        config = Config(root=filename_parent)
    else:
        # Unsaved files.
        config = Config(root=project_root)
    robocop_runner = robocop.Robocop(config=config)
    robocop_runner.reload_config()

    issues = robocop_runner.run_check(ast_model, filename, source)
    diag_issues = issues_to_lsp_diagnostic(issues)
    return diag_issues
