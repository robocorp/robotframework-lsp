import json
import sys
from typing import Any


def main() -> None:
    contents_to_lint: bytes = sys.stdin.buffer.read()
    try:
        from sema4ai import actions  # noqa #type: ignore

        use_sema4lib = True
    except ImportError:
        use_sema4lib = False

    EPManagedParameters: Any
    PluginManager: Any
    ManagedParameters: Any
    _lint_action: Any
    version_info: Any

    if use_sema4lib:
        from sema4ai.actions import _lint_action  # noqa #type: ignore
        from sema4ai.actions import version_info  # noqa #type: ignore

        requires_pm = True

        pm = None

        # fmt: off
        try:
            from sema4ai.actions._customization._extension_points import (  # noqa #type: ignore
                EPManagedParameters,
            )
            from sema4ai.actions._customization._plugin_manager import (  # noqa #type: ignore
                PluginManager,
            )
            from sema4ai.actions._managed_parameters import (  # noqa #type: ignore
                ManagedParameters,
            )


            pm = PluginManager()
            pm.set_instance(EPManagedParameters, ManagedParameters({}))
        except BaseException:
            pass
        # fmt: on
    else:
        try:
            # May not be in the target env or could be an older version of
            # robocorp.actions.
            from robocorp.actions import _lint_action  # noqa #type: ignore
            from robocorp.actions import version_info  # noqa #type: ignore

            requires_pm = version_info[:2] >= [0, 2]
        except BaseException:
            return

        pm = None
        if requires_pm:
            # fmt: off
            try:
                from robocorp.actions._managed_parameters import (  # noqa #type: ignore
                    ManagedParameters,
                )
                from robocorp.tasks._customization._extension_points import (  # noqa #type: ignore
                    EPManagedParameters,
                )
                from robocorp.tasks._customization._plugin_manager import (  # noqa #type: ignore
                    PluginManager,
                )

                pm = PluginManager()
                pm.set_instance(EPManagedParameters, ManagedParameters({}))
            except BaseException:
                pass
            # fmt: on

    if requires_pm:
        try:
            errors = list(_lint_action.iter_lint_errors(contents_to_lint, pm=pm))
        except BaseException:
            return
    else:
        try:
            errors = list(_lint_action.iter_lint_errors(contents_to_lint))
        except BaseException:
            return

    lst = []
    for error in errors:
        lsp_err = error.to_lsp_diagnostic()
        lsp_err["range"]["start"]["line"] -= 1
        lsp_err["range"]["end"]["line"] -= 1
        lst.append(lsp_err)

    print(json.dumps(lst))


if __name__ == "__main__":
    main()
