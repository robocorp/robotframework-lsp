""" optional jupyter[lab]_lsp integration
"""


def spec_v1(app):
    """A spec loader for jupyter_lsp"""
    return {
        "robotframework_ls": dict(
            version=2,
            argv=["robotframework_ls"],
            languages=["robotframework"],
            mime_types=["text/x-robotframework"],
            urls=dict(
                home="https://github.com/robocorp/robotframework-lsp",
                issues="https://github.com/robocorp/robotframework-lsp/issues",
            ),
            install=dict(
                pip="pip install robotframework-lsp",
                conda="conda install -c conda-forge robotframework-lsp",
            ),
        )
    }
