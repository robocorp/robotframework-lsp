import json
import sys


def main() -> None:
    contents_to_lint: bytes = sys.stdin.buffer.read()
    try:
        # May not be in the target env or could be an older version of
        # robocorp.actions.
        from robocorp.actions import _lint_action  # noqa #type: ignore
    except BaseException:
        return

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
