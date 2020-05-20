import os


def test_log(tmpdir):
    from robocode_ls_core.robotframework_log import get_logger, configure_logger
    from robocode_ls_core.unittest_tools.fixtures import wait_for_test_condition

    somedir = str(tmpdir.join("somedir"))
    configure_logger("test", 2, os.path.join(somedir, "foo.log"))

    log = get_logger("my_logger")
    log.info("something\nfoo\nbar")

    try:
        raise AssertionError("someerror")
    except:
        log.exception("rara: %s - %s", "str1", "str2")

    def get_log_files():
        log_files = [
            x for x in os.listdir(somedir) if x.startswith("foo") and x.endswith(".log")
        ]
        return log_files if log_files else None

    wait_for_test_condition(
        get_log_files, msg=lambda: "Found: %s in %s" % (get_log_files(), somedir)
    )
    log_files = get_log_files()

    with open(os.path.join(somedir, log_files[0]), "r") as stream:
        contents = stream.read()
        assert "someerror" in contents
        assert "something" in contents
        assert "rara" in contents
        assert "rara: str1 - str2" in contents
