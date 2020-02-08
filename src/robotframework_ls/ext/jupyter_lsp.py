""" optional jupyter[lab]_lsp integration
"""


def spec_v1(app):
    """ A spec loader for jupyter_lsp
    """
    return {
        "robotframework_ls": dict(
            version=1,
            argv=["robotframework_ls"],
            languages=["robotframework", "plain"],
            mime_types=["text/x-robotframework"],
            urls=dict(
                home="https://github.com/robocorp/robotframework-lsp",
                issues="https://github.com/robocorp/robotframework-lsp/issues",
            ),
        )
    }
