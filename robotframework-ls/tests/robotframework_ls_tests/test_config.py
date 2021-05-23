import pytest
import os


def test_config_basic():
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


def test_config_variable_resolution(monkeypatch):
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_PYTHON_EXECUTABLE,
    )
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    monkeypatch.setenv("FOO", "22")
    config = RobotConfig()
    settings = {
        "robot": {
            "python": {"executable": "${env.FOO}"},
            "variables": {"VAR1": "~/foo${env.FOO}/${env.FOO}"},
            "pythonpath": ["~/foo${env.FOO}/${env.FOO}", "${workspace}/a"],
        }
    }
    config.update(settings)
    assert config.get_setting(OPTION_ROBOT_PYTHON_EXECUTABLE, str) == "22"
    assert config.get_setting(OPTION_ROBOT_VARIABLES, dict) == {
        "VAR1": os.path.expanduser("~") + "/foo22/22"
    }
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list) == [
        os.path.expanduser("~") + "/foo22/22",
        "${workspace}/a",
    ]

    config.set_workspace_dir("workspacepath")
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list) == [
        os.path.expanduser("~") + "/foo22/22",
        "workspacepath/a",
    ]


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
