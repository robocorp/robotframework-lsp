from robocorp_ls_core.protocols import Sentinel, IConfig
from robocorp_ls_core.options import USE_TIMEOUTS
import enum
from typing import Optional
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


_DEFAULT_GENERAL_TIMEOUT: int = 20
_DEFAULT_COLLECT_DOCS_TIMEOUT: int = 60
_DEFAULT_LIST_TESTS_TIMEOUT: int = 40

# A whole month of timeout seems good enough as a max.
_BIG_TIMEOUT: int = 60 * 60 * 24 * 30

if not USE_TIMEOUTS:
    _DEFAULT_GENERAL_TIMEOUT = _BIG_TIMEOUT
    _DEFAULT_COLLECT_DOCS_TIMEOUT = _DEFAULT_GENERAL_TIMEOUT
    _DEFAULT_LIST_TESTS_TIMEOUT = _DEFAULT_GENERAL_TIMEOUT


class TimeoutReason(enum.Enum):
    general = "general"
    completion = "completions"
    code_formatting = "codeFormatting"
    collect_docs_timeout = "collectDocsTimeout"
    list_tests_timeout = "listTestsTimeout"


_reason_to_default_timeout = {
    TimeoutReason.collect_docs_timeout: _DEFAULT_COLLECT_DOCS_TIMEOUT,
    TimeoutReason.list_tests_timeout: _DEFAULT_LIST_TESTS_TIMEOUT,
}

_MIN_TIMEOUT: int = 5


def get_timeout(
    config: Optional[IConfig],
    reason: TimeoutReason,
    override=Sentinel.USE_DEFAULT_TIMEOUT,
) -> int:
    timeout = _internal_get_timeout(config, reason, override)
    if timeout <= 0:
        return _BIG_TIMEOUT

    if timeout < _MIN_TIMEOUT:
        log.info(
            "Timeout for %s set too low (%s) -- changing to %s seconds.",
            reason,
            timeout,
            _MIN_TIMEOUT,
        )
        return _MIN_TIMEOUT
    return timeout


def _internal_get_timeout(
    config: Optional[IConfig],
    reason: TimeoutReason,
    override=Sentinel.USE_DEFAULT_TIMEOUT,
) -> int:
    if override is not Sentinel.USE_DEFAULT_TIMEOUT:
        return override

    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_TIMEOUT_USE,
    )

    if config and not config.get_setting(OPTION_ROBOT_TIMEOUT_USE, bool, USE_TIMEOUTS):
        return _BIG_TIMEOUT

    if not USE_TIMEOUTS:
        return _BIG_TIMEOUT

    default = _reason_to_default_timeout.get(reason, _DEFAULT_GENERAL_TIMEOUT)
    if config:
        setting_name = f"robot.timeout.{reason.value}"
        try:
            return int(config.get_setting(setting_name, (int, str), default))
        except:
            log.exception("Error getting setting: %s", setting_name)
    return default
