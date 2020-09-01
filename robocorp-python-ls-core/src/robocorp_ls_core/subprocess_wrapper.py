import subprocess


def _fix_subprocess():
    import sys
    from robocorp_ls_core.constants import IS_PY37_ONWARDS

    # Workaround for https://bugs.python.org/issue37380 in older versions of Python.
    # i.e.: OSError: [WinError 6] The handle is invalid
    if IS_PY37_ONWARDS:
        return  # This is fixed in 3.7 onwards.

    _cleanup = (
        subprocess._cleanup
    )  # Just check that there is in fact a _cleanup attribute there.

    def _new_cleanup():
        for inst in subprocess._active[:]:
            try:
                res = inst._internal_poll(_deadstate=sys.maxsize)
            except OSError:
                res = 1  # This is the fix.
            if res is not None:
                try:
                    subprocess._active.remove(inst)
                except ValueError:
                    # This can happen if two threads create a new Popen instance.
                    # It's harmless that it was already removed, so ignore.
                    pass

    subprocess._cleanup = _new_cleanup


_fix_subprocess()
