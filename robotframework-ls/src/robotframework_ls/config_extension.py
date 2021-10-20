from typing import Optional

from robocorp_ls_core.ep_resolve_interpreter import IInterpreterInfo
from robocorp_ls_core.protocols import IConfig


def apply_interpreter_info_to_config(
    config: IConfig, interpreter_info: Optional[IInterpreterInfo]
):
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHON_ENV
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_PYTHON_EXECUTABLE,
    )
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    if interpreter_info is not None:
        overridden_settings: dict = {}
        python_exe = interpreter_info.get_python_exe()
        if python_exe:
            overridden_settings[OPTION_ROBOT_PYTHON_EXECUTABLE] = python_exe

        environ = interpreter_info.get_environ()
        if environ:
            overridden_settings[OPTION_ROBOT_PYTHON_ENV] = environ

        additional_pythonpath_entries = (
            interpreter_info.get_additional_pythonpath_entries()
        )
        if additional_pythonpath_entries:
            overridden_settings[OPTION_ROBOT_PYTHONPATH] = additional_pythonpath_entries
        else:
            # If we're applying the interpreter info, the pythonpath should be given
            # by it and if not available it should be overridden.
            overridden_settings[OPTION_ROBOT_PYTHONPATH] = []

        config.set_override_settings(overridden_settings)
    else:
        config.set_override_settings({})
