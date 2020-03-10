# Copyright 2009 Brian Quinlan. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""Execute computations asynchronously using threads or processes."""

__author__ = "Brian Quinlan (brian@sweetapp.com)"

from robotframework_ls.libs_py2.concurrent.futures._base import (
    FIRST_COMPLETED,
    FIRST_EXCEPTION,
    ALL_COMPLETED,
    CancelledError,
    TimeoutError,
    Future,
    Executor,
    wait,
    as_completed,
)
from robotframework_ls.libs_py2.concurrent.futures.thread import ThreadPoolExecutor

try:
    from robotframework_ls.libs_py2.concurrent.futures.process import (
        ProcessPoolExecutor,
    )
except ImportError:
    # some platforms don't have multiprocessing
    pass
