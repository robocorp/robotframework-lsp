import enum
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import ContextManager, Optional

from robocorp_ls_core.protocols import check_implements
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.protocols import IRCCSpaceInfo

log = get_logger(__name__)


class CurrentSpaceStatus(enum.Enum):
    # Still not checked
    UNDEFINED = 0

    # Ok, it can be used as is directly
    CAN_USE = 1

    # It's not available to reuse. i.e.: the conda contents don't match
    # and the timeout to reuse hasn't elapsed.
    NOT_AVAILABLE = 2

    # Ok, this is a valid reuse target.
    REUSE_TARGET = 3


class SpaceState(enum.Enum):
    CREATED = "created"
    ENV_REQUESTED = "environment_requested"
    ENV_READY = "environment_ready"


def write_text(path: Path, contents, encoding="utf-8"):
    try:
        path.write_text(contents, encoding, errors="replace")
    except:
        log.exception("Error writing to: %s", path)


@dataclass
class RCCSpaceInfo:
    space_name: str
    space_path: Path
    curr_status: CurrentSpaceStatus
    last_usage: float

    @property
    def conda_contents_path(self) -> Path:
        return self.space_path / "conda.yaml"

    @property
    def state_path(self) -> Path:
        return self.space_path / "state"

    @property
    def damaged_path(self) -> Path:
        return self.space_path / "damaged"

    @property
    def conda_path(self) -> Path:
        return self.space_path / "conda_path"

    @property
    def env_json_path(self) -> Path:
        return self.space_path / "env.json"

    @property
    def requested_pid_path(self) -> Path:
        return self.space_path / "pid"

    def load_last_usage(self, none_if_not_found: bool = False) -> Optional[float]:
        target = self.space_path / f"time_touch"
        if target.exists():
            last_usage = target.stat().st_mtime
            self.last_usage = last_usage
            return last_usage

        # Old code (the code used to write 'time_timespamp' i.e.: time_9302943342
        # but it's now upgraded to use a `time_touch` file which is just touched
        # to upgrade the time).
        found = []
        for entry in os.scandir(self.space_path):
            if entry.name.startswith("time_"):
                try:
                    time_as_float = float(entry.name[5:])
                except:
                    continue

                found.append((entry, time_as_float))

        found = sorted(found, key=lambda tup: tup[1])
        if not found:
            if none_if_not_found:
                return None

            log.info("Did not find the time at folder: %s", self.space_path)
            # Something is off, mark it as damaged and update the last usage.
            write_text(self.damaged_path, "damaged", "utf-8")
            last_usage = self.update_last_usage()
        else:
            # Ok, we have it. Lets erase the older entries.
            _, last_usage = found.pop()
            for entry, _ in found:
                target = self.space_path / entry.name
                try:
                    os.remove(target)
                except:
                    log.exception(f"Error removing: {target}.")

        self.last_usage = last_usage
        return last_usage

    def update_last_usage(self) -> float:
        target = self.space_path / f"time_touch"
        target.touch()
        last_usage = target.stat().st_mtime
        self.last_usage = last_usage
        return last_usage

    def load_requested_pid(self) -> str:
        try:
            return self.requested_pid_path.read_text("utf-8")
        except:
            return ""

    def has_timeout_elapsed(self, timeout_to_reuse_space: float) -> bool:
        curtime = time.time()
        last_usage = self.load_last_usage()
        assert last_usage is not None

        has_timeout_elapsed = curtime > last_usage + timeout_to_reuse_space
        return has_timeout_elapsed

    def pretty(self):
        import textwrap
        from dataclasses import fields

        ret = ["RCCSpaceInfo:"]
        for field in fields(self):
            try:
                value = getattr(self, field.name)
                if isinstance(value, Path):
                    path = value
                    if value.is_dir():
                        value = f"{path} (directory)"
                    else:
                        if not path.exists():
                            value = f"{path} (does not exist)"
                        else:
                            try:
                                contents = textwrap.indent(
                                    path.read_text("utf-8", "replace"), "        "
                                )
                                contents = " (file)\n" + contents
                                value = str(path) + contents
                            except:
                                value = f"<unable to read: {path}>"
            except:
                value = "<unable to get attr>"
            ret.append(f"    {field.name}={value}")
        return "\n".join(ret)

    @classmethod
    def from_directory(
        cls,
        base_directory: Path,
        space_name: str,
        curr_status: CurrentSpaceStatus = CurrentSpaceStatus.UNDEFINED,
        last_usage: float = 0,
    ) -> "RCCSpaceInfo":
        space_path = base_directory / space_name
        return cls(
            space_name=space_name,
            space_path=space_path,
            curr_status=curr_status,
            last_usage=last_usage,
        )

    def acquire_lock(self) -> ContextManager:
        from robocorp_ls_core.system_mutex import timed_acquire_mutex

        return timed_acquire_mutex(
            f"{self.space_name}.lock", timeout=60, base_dir=str(self.space_path.parent)
        )

    def conda_contents_match(self, conda_yaml_contents: str) -> bool:
        contents = self.conda_contents_path.read_text("utf-8")

        formatted = format_conda_contents_to_compare(contents)
        return formatted == format_conda_contents_to_compare(conda_yaml_contents)

    def matches_conda_identity_yaml(self, conda_id: Path) -> bool:
        try:
            contents = self.conda_contents_path.read_text("utf-8")
            return format_conda_contents_to_compare(
                contents
            ) == format_conda_contents_to_compare(
                conda_id.read_text("utf-8", "replace")
            )
        except:
            log.error("Error when loading yaml to verify conda identity match.")
            return False

    def conda_prefix_identity_yaml_still_matches_cached_space(self):
        try:
            import json

            environ = json.loads(
                self.env_json_path.read_text("utf-8", errors="replace")
            )
        except:
            log.error("Error loading environment from: %s", self.env_json_path)
            return False

        conda_prefix = environ.get("CONDA_PREFIX")
        if conda_prefix is None:
            log.critical(
                f"Expected CONDA_PREFIX to be available in the environ. Found: {environ}."
            )
            return False

        conda_id = Path(conda_prefix) / "identity.yaml"
        if not self.matches_conda_identity_yaml(conda_id):
            log.critical(
                f"The conda contents in: {conda_id} do not match the contents from {self.conda_contents_path}."
            )
            return False

        return True

    def __typecheckself__(self) -> None:
        _: IRCCSpaceInfo = check_implements(self)


@lru_cache(maxsize=50)
def format_conda_contents_to_compare(contents: str) -> str:
    try:
        from robocorp_ls_core import yaml_wrapper

        load_yaml = yaml_wrapper.load
        loaded = load_yaml(contents)
        return repr(loaded)
    except:
        log.info("Unable to parse yaml: %s", contents)
        lst = []
        for line in contents.splitlines(keepends=False):
            line = line.strip()
            if not line:
                continue
            lst.append(line)
        return "".join(lst)
