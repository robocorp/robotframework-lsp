def test_disable_timeouts(monkeypatch):
    from robocorp_ls_core.config import Config
    from robotframework_ls.ls_timeouts import get_timeout
    from robotframework_ls.ls_timeouts import TimeoutReason
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_TIMEOUT_COLLECT_DOCS_TIMEOUT,
    )
    from robocorp_ls_core.protocols import Sentinel
    from robotframework_ls import ls_timeouts
    from robotframework_ls.ls_timeouts import _BIG_TIMEOUT
    from robotframework_ls.ls_timeouts import _MIN_TIMEOUT

    monkeypatch.setattr(ls_timeouts, "_DEFAULT_GENERAL_TIMEOUT", 7)
    monkeypatch.setattr(ls_timeouts, "_DEFAULT_COLLECT_DOCS_TIMEOUT", 8)
    monkeypatch.setattr(ls_timeouts, "_DEFAULT_LIST_TESTS_TIMEOUT", 9)
    monkeypatch.setattr(ls_timeouts, "USE_TIMEOUTS", True)

    config = Config()
    config.update({OPTION_ROBOT_TIMEOUT_COLLECT_DOCS_TIMEOUT: 22})
    assert get_timeout(config, TimeoutReason.collect_docs_timeout) == 22
    assert get_timeout(config, TimeoutReason.collect_docs_timeout, 33) == 33
    assert (
        get_timeout(
            config, TimeoutReason.collect_docs_timeout, Sentinel.USE_DEFAULT_TIMEOUT
        )
        == 22
    )

    config.update({OPTION_ROBOT_TIMEOUT_COLLECT_DOCS_TIMEOUT: 0})
    assert get_timeout(config, TimeoutReason.collect_docs_timeout) == _BIG_TIMEOUT
    config.update({OPTION_ROBOT_TIMEOUT_COLLECT_DOCS_TIMEOUT: -1})
    assert get_timeout(config, TimeoutReason.collect_docs_timeout) == _BIG_TIMEOUT
    config.update({OPTION_ROBOT_TIMEOUT_COLLECT_DOCS_TIMEOUT: 1})
    assert get_timeout(config, TimeoutReason.collect_docs_timeout) == _MIN_TIMEOUT

    from robotframework_ls.ls_timeouts import _DEFAULT_GENERAL_TIMEOUT

    assert get_timeout(config, TimeoutReason.general) == _DEFAULT_GENERAL_TIMEOUT

    config.update({"robot.timeout.use": False})
    assert get_timeout(config, TimeoutReason.general) == _BIG_TIMEOUT
    assert get_timeout(config, TimeoutReason.collect_docs_timeout) == _BIG_TIMEOUT
    assert get_timeout(config, TimeoutReason.collect_docs_timeout, 33) == 33
