__version__ = "1.6.0"
version_info = [int(x) for x in __version__.split(".")]

import os.path
import sys

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]


def import_robocorp_ls_core():
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
            src_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_contents.append("Source folder: %s" % (src_folder,))
            src_core_folder = os.path.abspath(
                os.path.join(src_folder, "..", "..", "robocorp-python-ls-core", "src")
            )

            if os.path.isdir(src_core_folder):
                log_contents.append("Dev mode detected. Found: %s" % (src_core_folder,))
                use_folder = src_core_folder

            else:
                vendored_folder = os.path.join(
                    src_folder, "robotframework_ls", "vendored"
                )
                log_contents.append(
                    "Using vendored mode. Found: %s" % (vendored_folder,)
                )
                use_folder = vendored_folder
                assert os.path.isdir(
                    use_folder
                ), "Expected: %s to exist and be a directory." % (use_folder,)

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


def _import_helper(import_callback, project_name):
    try:
        import_callback()
    except ImportError:
        log_contents = []
        try:
            src_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_contents.append("Source folder: %s" % (src_folder,))
            check_path = [src_folder, "..", "..", project_name, "src"]
            src_core_folder = os.path.abspath(os.path.join(*check_path))

            if os.path.isdir(src_core_folder):
                log_contents.append("Dev mode detected. Found: %s" % (src_core_folder,))
                use_folder = src_core_folder

            else:
                vendored_folder = os.path.join(
                    src_folder, "robotframework_ls", "vendored"
                )
                log_contents.append(
                    "Using vendored mode. Found: %s" % (vendored_folder,)
                )
                use_folder = vendored_folder
                assert os.path.isdir(
                    use_folder
                ), "Expected: %s to exist and be a directory." % (use_folder,)

            sys.path.append(use_folder)
            import_callback()
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


def import_rf_interactive():
    """
    Helper function to make sure that robotframework_interactive is imported properly
    (either in dev or in release mode).
    """

    def import_callback():
        import robotframework_interactive

    _import_helper(import_callback, "robotframework-interactive")


def import_robot_out_stream():
    """
    Helper function to make sure that robot_out_stream is imported properly
    (either in dev or in release mode).
    """

    def import_callback():
        import robot_out_stream

    _import_helper(import_callback, "robotframework-output-stream")
