# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

from __future__ import absolute_import, division, print_function, unicode_literals

import contextlib
from importlib import import_module
import os
import sys
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)

VENDORED_ROOT = os.path.dirname(os.path.abspath(__file__))


def project_root(project):
    """Return the path to the root dir of the vendored project.

    If "project" is an empty string then the path prefix for vendored
    projects (e.g. "robotframework_debug_adapter/_vendored/") will be returned.
    """
    if not project:
        project = ""
    return os.path.join(VENDORED_ROOT, project)


@contextlib.contextmanager
def vendored(project, root=None):
    """A context manager under which the vendored project will be imported."""
    if root is None:
        root = project_root(project)
    # Add the vendored project directory, so that it gets tried first.
    sys.path.insert(0, root)
    try:
        yield root
    finally:
        sys.path.remove(root)


def preimport(project, modules, **kwargs):
    """Import each of the named modules out of the vendored project."""
    with vendored(project, **kwargs):
        for name in modules:
            import_module(name)


try:
    import pydevd  # noqa
except ImportError:
    pydevd_available = False
else:
    pydevd_available = True


if not pydevd_available:
    # Constants must be set before importing any other pydevd module
    # # due to heavy use of "from" in them.
    with vendored("vendored_pydevd"):
        try:
            pydevd_constants = import_module("_pydevd_bundle.pydevd_constants")
        except ImportError as e:
            contents = os.listdir(VENDORED_ROOT)

            for c in contents[:]:
                if os.path.isdir(c):
                    contents.append(f"{c}/{os.listdir(c)}")
                else:
                    contents.append(c)

            s = "\n".join(contents)

            msg = f"Vendored root: {VENDORED_ROOT} -- contents:\n{s}"
            raise ImportError(msg) from e

    # Now make sure all the top-level modules and packages in pydevd are
    # loaded.  Any pydevd modules that aren't loaded at this point, will
    # be loaded using their parent package's __path__ (i.e. one of the
    # following).
    preimport(
        "vendored_pydevd",
        [
            "_pydev_bundle",
            "_pydev_runfiles",
            "_pydevd_bundle",
            "_pydevd_frame_eval",
            "pydev_ipython",
            "pydevd_plugins",
            "pydevd",
        ],
    )

import pydevd  # noqa

log.info("Vendored root: %s\npydevd: %s", VENDORED_ROOT, pydevd)

# Ensure that pydevd uses JSON protocol by default.
from _pydevd_bundle import pydevd_constants
from _pydevd_bundle import pydevd_defaults

pydevd_defaults.PydevdCustomization.DEFAULT_PROTOCOL = (
    pydevd_constants.HTTP_JSON_PROTOCOL
)


from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import (
    BaseSchema as RobotSchema,
)
from _pydevd_bundle._debug_adapter.pydevd_base_schema import BaseSchema as PyDevdSchema

PyDevdSchema._obj_id_to_dap_id = RobotSchema._obj_id_to_dap_id
PyDevdSchema._dap_id_to_obj_id = RobotSchema._dap_id_to_obj_id
PyDevdSchema._next_dap_id = RobotSchema._next_dap_id
