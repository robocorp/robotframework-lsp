__version__ = "0.0.1"
from typing import List

version_info: List[int] = [int(x) for x in __version__.split(".")]

import os
import sys


def get_src_folder() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def import_robocorp_ls_core() -> None:
    """
    Helper function to make sure that robocorp_ls_core is imported properly
    (either in dev or in release mode).
    """

    try:
        import robocorp_ls_core
    except ImportError:
        log_contents = []
        use_folder = None
        try:
            src_folder = get_src_folder()
            log_contents.append("Source folder: %s" % (src_folder,))
            src_core_folder = os.path.abspath(
                os.path.join(src_folder, "..", "..", "robocorp-python-ls-core", "src")
            )

            if os.path.isdir(src_core_folder):
                log_contents.append("Dev mode detected. Found: %s" % (src_core_folder,))
                use_folder = src_core_folder

            else:
                # If not in dev, it's expected to be vendored just like it (so, it
                # should be alongside it).
                use_folder = src_folder
                log_contents.append("Using vendored mode. Found: %s" % (use_folder,))
                assert os.path.isdir(use_folder), (
                    "Expected: %s to exist and be a directory." % (use_folder,)
                )

            sys.path.append(use_folder)
            import robocorp_ls_core
        except:
            try:
                if use_folder:
                    log_contents.append(
                        "%s contents:\n%s" % (use_folder, os.listdir(use_folder))
                    )
            except:
                log_contents.append("Error in os.listdir('%s')." % (use_folder,))
            raise ImportError(
                "Error importing robocorp_ls_core. Log: %s" % "\n".join(log_contents)
            )
