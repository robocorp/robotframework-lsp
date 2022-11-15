This folder contains the `robocorp_ls_core` files which are vendored on release.

The `robocorp_ls_core` files are copied at build time and are distributed
along the language server (and when running the extension this folder
is added to the PYTHONPATH when needed).

During development this is not needed (`robocorp-python-ls-core/src` should be
added the PYTHONPATH instead).

To vendor the proper contents, use:

python -m dev vendor-robocorp-ls-core
python -m dev vendor-robotframework-interactive
python -m dev vendor-robotframework-output-stream