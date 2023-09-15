import os.path
from pathlib import Path
import sys
from typing import List

from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.lsp import DiagnosticsTypedDict
import typing


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
) -> List[DiagnosticsTypedDict]:
    _import_robocop()

    import robocop
    from robocop.config import Config
    from robocop.utils import issues_to_lsp_diagnostic

    filename_parent = Path(filename).parent
    # Set the working directory to the project root (tricky handling: Robocop
    # relies on cwd to deal with the --ext-rules
    # See: https://github.com/robocorp/robotframework-lsp/issues/703).
    initial_cwd = os.getcwd()
    try:
        if os.path.exists(project_root):
            os.chdir(project_root)

        if filename_parent.exists():
            config = Config(root=filename_parent)
        else:
            # Unsaved files.
            config = Config(root=project_root)
        robocop_runner = robocop.Robocop(config=config)
        robocop_runner.reload_config()

        issues = robocop_runner.run_check(ast_model, filename, source)
        diag_issues = typing.cast(
            List[DiagnosticsTypedDict], issues_to_lsp_diagnostic(issues)
        )
    finally:
        os.chdir(initial_cwd)
    return diag_issues
