import pytest


def test_config(tmpdir):
    from robotframework_ls.config.config import Config

    config = Config(
        root_uri=str(tmpdir), init_opts={}, process_id=None, capabilities={}
    )
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
    assert config.get_setting("robot.python.executable", str) == "foobar"
    assert config.get_setting("robot.language-server.tcp-port", int) == 1456

    # i.e.: convert to type when possible
    assert config.get_setting("robot.python.value", int) == 10
    assert config.get_setting("robot.python.value_float", float) == 10.5

    with pytest.raises(KeyError):
        config.get_setting("robot.python.value_float", int)

    with pytest.raises(KeyError):
        assert config.get_setting("robot.not_there", int)
