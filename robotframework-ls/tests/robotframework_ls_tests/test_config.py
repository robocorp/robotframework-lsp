import pytest


def test_config():
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_PYTHON_EXECUTABLE,
    )
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_LANGUAGE_SERVER_TCP_PORT,
    )

    config = RobotConfig()
    settings = {
        "robot": {
            "language-server": {
                "tcp-port": 1456,
                "args": ["-vv", "--log-file=~/robotframework_ls.log"],
            },
            "python": {"executable": "foobar", "value": "10", "value_float": "10.5"},
        }
    }
    config.update(settings)
    assert config.get_setting(OPTION_ROBOT_PYTHON_EXECUTABLE, str) == "foobar"
    assert config.get_setting(OPTION_ROBOT_LANGUAGE_SERVER_TCP_PORT, int) == 1456

    # i.e.: convert to type when possible
    assert config.get_setting("robot.python.value", int) == 10
    assert config.get_setting("robot.python.value_float", float) == 10.5

    with pytest.raises(KeyError):
        config.get_setting("robot.python.value_float", int)

    with pytest.raises(KeyError):
        assert config.get_setting("robot.not_there", int)


def test_config_flatten_01():
    from robocorp_ls_core import config
    from robotframework_ls.impl.robot_lsp_constants import ALL_ROBOT_OPTIONS

    settings = {
        "robot": {
            "language-server": {
                "tcp-port": 1456,
                "args": ["-vv", "--log-file=~/robotframework_ls.log"],
            },
            "python": {"executable": "foobar", "value": "10", "value_float": "10.5"},
        },
        "robot.variables": {"var1": 10, "var2": 20},
    }
    assert config.flatten_keys(settings, all_options=ALL_ROBOT_OPTIONS) == {
        "robot.language-server.tcp-port": 1456,
        "robot.language-server.args": ["-vv", "--log-file=~/robotframework_ls.log"],
        "robot.python.executable": "foobar",
        "robot.python.value": "10",
        "robot.python.value_float": "10.5",
        "robot.variables": {"var1": 10, "var2": 20},
    }


def test_config_flatten_02():
    from robocorp_ls_core import config
    from robotframework_ls.impl.robot_lsp_constants import ALL_ROBOT_OPTIONS

    settings = {
        "robot": {
            "language-server": {
                "tcp-port": 1456,
                "args": ["-vv", "--log-file=~/robotframework_ls.log"],
            },
            "python": {"executable": "foobar", "value": "10", "value_float": "10.5"},
            "variables": {"var1": 10, "var2": 20},
        }
    }
    assert config.flatten_keys(settings, all_options=ALL_ROBOT_OPTIONS) == {
        "robot.language-server.tcp-port": 1456,
        "robot.language-server.args": ["-vv", "--log-file=~/robotframework_ls.log"],
        "robot.python.executable": "foobar",
        "robot.python.value": "10",
        "robot.python.value_float": "10.5",
        "robot.variables": {"var1": 10, "var2": 20},
    }
