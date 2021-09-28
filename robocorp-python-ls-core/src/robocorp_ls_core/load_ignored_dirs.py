import os
from typing import Optional, Dict
import fnmatch
import glob

from robocorp_ls_core.robotframework_log import get_logger


log = get_logger(__name__)


def _load_ignored_dirs_patterns(additional_dirs_to_ignore_str: Optional[str] = None):
    ignored_dirs_patterns = set()
    if additional_dirs_to_ignore_str is None:
        additional_dirs_to_ignore_str = os.environ.get("ROBOTFRAMEWORK_LS_IGNORE_DIRS")

    if additional_dirs_to_ignore_str:
        import json

        try:
            additional_dirs_to_ignore = json.loads(additional_dirs_to_ignore_str)
        except:
            log.exception(
                "Unable to load: %s (expected it to be a json list).",
                additional_dirs_to_ignore_str,
            )
        else:
            log.info(
                "Loaded ROBOTFRAMEWORK_LS_IGNORE_DIRS: %s", additional_dirs_to_ignore
            )
            if isinstance(additional_dirs_to_ignore, list):
                for entry in additional_dirs_to_ignore:
                    if isinstance(entry, str):
                        ignored_dirs_patterns.add(entry)
                    else:
                        log.critical(
                            "Unable to load entry: %s from %s (because it's not a string).",
                            entry,
                            additional_dirs_to_ignore,
                        )
            else:
                log.critical(
                    "Unable to load: %s (because it's not a list).",
                    additional_dirs_to_ignore_str,
                )

    return ignored_dirs_patterns


normcase = os.path.normcase


def _check_matches(patterns, paths):
    if not patterns and not paths:
        # Matched to the end.
        return True

    if (not patterns and paths) or (patterns and not paths):
        return False

    pattern = normcase(patterns[0])
    path = normcase(paths[0])

    if not glob.has_magic(pattern):

        if pattern != path:
            return False

    elif pattern == "**":
        if len(patterns) == 1:
            return True  # if ** is the last one it matches anything to the right.

        for i in range(len(paths)):
            # Recursively check the remaining patterns as the
            # current pattern could match any number of paths.
            if _check_matches(patterns[1:], paths[i:]):
                return True

    elif not fnmatch.fnmatch(path, pattern):
        # Current part doesn't match.
        return False

    return _check_matches(patterns[1:], paths[1:])


def glob_matches_path(path, pattern, sep=os.sep, altsep=os.altsep):
    if altsep:
        pattern = pattern.replace(altsep, sep)
        path = path.replace(altsep, sep)

    drive = ""
    if len(path) > 1 and path[1] == ":":
        drive, path = path[0], path[2:]

    if drive and len(pattern) > 1:
        if pattern[1] == ":":
            if drive.lower() != pattern[0].lower():
                return False
            pattern = pattern[2:]

    patterns = pattern.split(sep)
    paths = path.split(sep)
    if paths:
        if paths[0] == "":
            paths = paths[1:]
    if patterns:
        if patterns[0] == "":
            patterns = patterns[1:]

    return _check_matches(patterns, paths)


def create_accept_directory_callable(
    additional_dirs_to_ignore_str: Optional[str] = None,
):
    ignored_dirs = {
        "**/.git",
        "**/__pycache__",
        "**/.idea",
        "**/node_modules",
        "**/.metadata",
        "**/.vscode",
    }

    ignored_dirs.update(_load_ignored_dirs_patterns(additional_dirs_to_ignore_str))

    def accept_directory(dir_path: str, *, cache: Dict[str, bool] = {}):
        try:
            return cache[dir_path]
        except KeyError:
            for pattern in ignored_dirs:
                if glob_matches_path(dir_path, pattern):
                    cache[dir_path] = False
                    log.debug("Directory untracked for changes: %s", dir_path)
                    return False

            log.debug("Directory tracked for changes: %s", dir_path)
            cache[dir_path] = True
            return True

    return accept_directory
