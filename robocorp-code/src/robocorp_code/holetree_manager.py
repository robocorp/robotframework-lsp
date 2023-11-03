"""
The main reason for this class is managing the space name for holotrees.

The design is the following:

When a space name is requested, we collect/store the metadata based on the
request and then provide a space name based on what was previously requested
and the current request.

Note that there are a number of heuristics done to make sure that the request
is Ok.

Also, the space name is just a part of the info needed as after a name
is requested, we also need to consider that the environment isn't really
valid until the environment was actually created for the given space.

The structure goes as follows:

Each request for a space name creates a structure in the disk such as:

/vscode-01.lock     Lock file used, needed to write contents and generate the env. 
/vscode-01          The directory name as well as the space name.
    /time           The last time that this space name was used.
    /conda.yaml     The contents used for the space name.
    /conda_path     The path to the conda file last used for this env.
    /state          The current state name. 
                    It's contents are one of:
                       'created'
                       'environment_requested'
                       'environment_ready'
                    Depending on the current state of the space.
    /env.json       A Json with the environment for this space.
                    Note that it's created later on, after the environment
                    is actually created.
    /damaged        Written if the space is to be considered damaged
                    and should be reclaimed after a timeout.
"""


from pathlib import Path
from typing import Iterable, List, Optional

from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.protocols import IRcc
from robocorp_code.rcc_space_info import (
    CurrentSpaceStatus,
    RCCSpaceInfo,
    SpaceState,
    write_text,
)

log = get_logger(__name__)


_TWO_HOURS_IN_SECONDS = 60 * 60 * 2


class UnableToGetSpaceName(RuntimeError):
    pass


class HolotreeManager:
    def __init__(
        self,
        rcc: IRcc,
        directory: Optional[Path] = None,
        max_number_of_spaces: int = 10,
        timeout_for_updates_in_seconds: int = 10,
        # We can only reclaim a space after 2 hours without usage.
        timeout_to_reuse_space: int = _TWO_HOURS_IN_SECONDS,
    ):
        """
        :param directory:
            This is the directory where the holotree manager can store/load
            info.

            Usually it should not be passed and it defaults to something
            as ROBOCORP_HOME/.vscode (but a different path can be used for
            tests).
        """
        self._rcc = rcc
        self.timeout_for_updates_in_seconds = timeout_for_updates_in_seconds
        if not directory:
            robocorp_home_str = self._rcc.get_robocorp_home_from_settings()
            if not robocorp_home_str:
                from robocorp_code.rcc import get_default_robocorp_home_location

                robocorp_home = get_default_robocorp_home_location()
            else:
                robocorp_home = Path(robocorp_home_str)

            directory = robocorp_home / ".robocorp_code"

        directory.mkdir(parents=True, exist_ok=True)

        self._directory = directory
        self._max_number_of_spaces = max_number_of_spaces
        self._timeout_to_reuse_space = timeout_to_reuse_space

    def _iter_target_space_names(self):
        i = 1
        while i < self._max_number_of_spaces + 1:
            yield "vscode-%02d" % i
            i += 1

    def create_rcc_space_info(
        self,
        space_name: str,
        curr_status: CurrentSpaceStatus = CurrentSpaceStatus.UNDEFINED,
        last_usage: float = 0,
    ) -> RCCSpaceInfo:
        return RCCSpaceInfo.from_directory(
            self._directory, space_name, curr_status, last_usage
        )

    def _compute_status(
        self, space_name: str, conda_yaml_path: Path, conda_yaml_contents: str
    ) -> RCCSpaceInfo:
        space_info: RCCSpaceInfo = self.create_rcc_space_info(space_name)
        conda_contents_path = space_info.conda_contents_path
        state_path = space_info.state_path
        conda_path = space_info.conda_path

        try:
            space_info.space_path.mkdir(parents=True, exist_ok=False)
            lock = space_info.acquire_lock()
        except:
            # Ok, there's already a folder with that name, which means that
            # there's a chance that this space is being used.
            # In this case, we have 2 choices:
            # 1. Reuse the space as is (if the contents are compatible).
            # 2. Bail out and note whether this state can be recreated.
            try:
                # Check for direct match. i.e.: let's see if we can use it as is.
                with space_info.acquire_lock():
                    if not self._info_in_place(conda_contents_path, space_info):
                        # If the info is not in place, something is off -- was the info
                        # corrupted? In any case this isn't a match and may be reused if
                        # the timeout has elapsed.
                        has_timeout_elapsed = space_info.has_timeout_elapsed(
                            self._timeout_to_reuse_space
                        )
                        if has_timeout_elapsed:
                            space_info.curr_status = CurrentSpaceStatus.REUSE_TARGET
                            return space_info
                        space_info.curr_status = CurrentSpaceStatus.NOT_AVAILABLE
                        return space_info

                    if space_info.conda_contents_match(conda_yaml_contents):
                        env_written = space_info.env_json_path.exists()
                        if (
                            env_written
                            and space_info.conda_prefix_identity_yaml_still_matches_cached_space()
                        ) or not env_written:
                            space_info.update_last_usage()
                            write_text(conda_path, str(conda_yaml_path), "utf-8")
                            space_info.curr_status = CurrentSpaceStatus.CAN_USE
                            return space_info
            except:
                # Just ignore (we couldn't read the conda text...).
                pass

            has_timeout_elapsed = space_info.has_timeout_elapsed(
                self._timeout_to_reuse_space
            )
            if has_timeout_elapsed:
                space_info.curr_status = CurrentSpaceStatus.REUSE_TARGET
                return space_info
            space_info.curr_status = CurrentSpaceStatus.NOT_AVAILABLE
            return space_info

        else:
            # Ok, we just created this dir, let's fill the space metadata
            # based on this request.
            with lock:
                space_info.update_last_usage()
                write_text(conda_contents_path, conda_yaml_contents, "utf-8")
                write_text(conda_path, str(conda_yaml_path), "utf-8")
                write_text(state_path, SpaceState.CREATED.value, "utf-8")
            space_info.curr_status = CurrentSpaceStatus.CAN_USE

            return space_info

    def _info_in_place(self, conda_yaml_path: Path, space_info: RCCSpaceInfo) -> bool:
        """
        :return: True if we have all the expected files, otherwise return False.
        """
        last_usage = space_info.load_last_usage(none_if_not_found=True)
        if space_info.damaged_path.exists():
            if last_usage is None:
                # It was damaged and the time is not there, rewrite the time.
                space_info.update_last_usage()
            return False

        found_structure = (
            conda_yaml_path.exists()
            and last_usage is not None
            and space_info.state_path.exists()
        )
        if found_structure:
            return True

        log.info("Marking as damaged: %s", space_info.damaged_path)
        write_text(space_info.damaged_path, "damaged", "utf-8")
        if last_usage is None:
            # If there's not even a time-path, we'll just write one
            # and after the proper amount of time passes it'll be recycled.
            space_info.update_last_usage()
        return False

    def _can_reuse_simple(
        self,
        conda_yaml_contents: str,
        conda_yaml_path: Path,
        space_info: RCCSpaceInfo,
        check_timeout: bool = True,
    ) -> bool:
        """
        Used to check reuse targets we found previously.
        """
        with space_info.acquire_lock():
            has_timeout_elapsed = space_info.has_timeout_elapsed(
                self._timeout_to_reuse_space
            )
            if has_timeout_elapsed or not check_timeout:
                # Ok, good to reuse, let's write the new info and proceed to use
                # this one.
                log.info("Reusing space after timeout: %s", space_info.space_name)
                space_info.update_last_usage()
                write_text(space_info.conda_contents_path, conda_yaml_contents, "utf-8")
                write_text(space_info.conda_path, str(conda_yaml_path), "utf-8")
                write_text(space_info.state_path, SpaceState.CREATED.value, "utf-8")
                return True

        return False

    def iter_existing_space_infos(self) -> Iterable[RCCSpaceInfo]:
        for space_name in self._iter_target_space_names():
            space_info = self.create_rcc_space_info(space_name)
            if space_info.space_path.exists():
                yield space_info

    def compute_valid_space_info(
        self,
        conda_yaml_path: Path,
        conda_yaml_contents: str,
        require_timeout: bool = False,
    ) -> RCCSpaceInfo:
        checked: List[str] = []
        can_reuse: List[RCCSpaceInfo] = []
        not_available: List[RCCSpaceInfo] = []
        for name in self._iter_target_space_names():
            checked.append(name)
            status = self._compute_status(name, conda_yaml_path, conda_yaml_contents)
            if status.curr_status == CurrentSpaceStatus.CAN_USE:
                return status
            elif status.curr_status == CurrentSpaceStatus.REUSE_TARGET:
                can_reuse.append(status)
            elif status.curr_status == CurrentSpaceStatus.NOT_AVAILABLE:
                not_available.append(status)

        if can_reuse:
            # Ok, we haven't found any readily available, but it seems we can
            # reuse an environment...
            can_reuse = sorted(
                can_reuse,
                key=lambda status: (
                    not status.damaged_path.exists(),
                    -status.last_usage,
                ),
            )
            for space_info in can_reuse:
                if self._can_reuse_simple(
                    conda_yaml_contents, conda_yaml_path, space_info
                ):
                    return space_info

        if not require_timeout:
            log.critical(
                f"Timeout hasn't passed for any env. Picking just based on LRU."
            )
            # Ok, we haven't found any readily available, so, reuse just based on LRU.
            all_envs = sorted(
                can_reuse + not_available,
                key=lambda status: (
                    not status.damaged_path.exists(),
                    -status.last_usage,
                ),
            )
            for space_info in all_envs:
                if self._can_reuse_simple(
                    conda_yaml_contents,
                    conda_yaml_path,
                    space_info,
                    check_timeout=False,
                ):
                    return space_info

        raise UnableToGetSpaceName("Unable to collect valid space info.")
