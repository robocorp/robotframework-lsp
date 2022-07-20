import json
import mock
import pytest
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from robotframework_ls import robotframework_ls_impl


# class for mocking RobotFrameworkLanguageServer as _config is not originally an attribute
# & Mock object is not serializable to be utilized as `self``
class MockRFLS:
    class MockConfig:
        def get_setting(*args, **kwards):
            pass

    _config = MockConfig()


def test_recursive_exploration(datadir):
    from robotframework_ls.impl.rf_model_builder import RFModelBuilder

    with open(os.path.join(datadir, "default_model_bot.json")) as model_json_file:
        model = json.load(model_json_file)

    task = model["tasks"][0]
    task["body"] = RFModelBuilder("test")._recursive_exploration(model, task)

    assert len(task["body"]) > 0
    assert task["body"][0]["name"] == "Main Implemented Keyword"
    assert len(task["body"][0]["body"]) > 0

    assert task["body"][0]["body"][0]["name"] == "Comment 1"


def test_recursive_exploration_infinite_fail(datadir):
    from robotframework_ls.impl.rf_model_builder import RFModelBuilder

    with open(
        os.path.join(datadir, "default_model_bot_infinite_loop.json")
    ) as model_json_file:
        model = json.load(model_json_file)
    task = model["tasks"][0]
    with pytest.raises(RecursionError):
        task["body"] = RFModelBuilder("test")._recursive_exploration(model, task)

    assert len(task["body"]) > 0
    assert task["body"][0]["name"] == "Main Implemented Keyword"
    assert len(task["body"][0]["body"]) == 0


def test_build_deep_model(datadir):
    from robotframework_ls.impl.rf_model_builder import RFModelBuilder

    with open(os.path.join(datadir, "default_model_bot.json")) as model_json_file:
        model = json.load(model_json_file)
    model = RFModelBuilder("test")._build_deep_model(model)
    task = model["tasks"][0]

    assert len(task["body"]) > 0
    assert task["body"][0]["name"] == "Main Implemented Keyword"
    assert len(task["body"][0]["body"]) > 0

    assert task["body"][0]["body"][0]["name"] == "Comment 1"


def test_build_deep_model_infinite_fail(datadir):
    from robotframework_ls.impl.rf_model_builder import RFModelBuilder

    with open(
        os.path.join(datadir, "default_model_bot_infinite_loop.json")
    ) as model_json_file:
        model = json.load(model_json_file)
    task = model["tasks"][0]
    with pytest.raises(RecursionError):
        RFModelBuilder("test")._build_deep_model(model)

    assert len(task["body"]) > 0
    assert task["body"][0]["name"] == "Main Implemented Keyword"
    assert len(task["body"][0]["body"]) == 0


@mock.patch.object(
    robotframework_ls_impl,
    "_FLOW_EXPLORER_BUNDLE_HTML_FILE_NAME",
    "original_html_file.html",
)
def test_open_flow_explorer(tmpdir, datadir):
    import re

    return_path = (
        robotframework_ls_impl.RobotFrameworkLanguageServer._open_flow_explorer(
            MockRFLS(),
            {
                "currentFileUri": os.path.join(datadir, "default_simple.robot"),
                "htmlBundleFolderPath": tmpdir,
            },
        )
    )

    return_uri = urlparse(return_path["uri"])
    tmp_bundle_html_file_path = Path(url2pathname(return_uri.path))
    assert tmp_bundle_html_file_path.exists()

    file_contents = tmp_bundle_html_file_path.read_text()
    assert '<div id="root"></div>' in file_contents
    assert '<script id="options" type="application/json">' in file_contents
    assert '"theme": ' in file_contents
    assert '"showCopyright": true' in file_contents
    assert '<script id="data" type="application/json">' in file_contents
    assert "Main Implemented Keyword" in file_contents
    assert "Third Implemented Keyword" in file_contents
    assert len(re.findall(r"file://.*\/favicon.png", file_contents)) == 1
    assert (
        len(re.findall(r"file://.*\/robot_flow_explorer_bundle.js", file_contents)) == 1
    )


@mock.patch.object(
    robotframework_ls_impl,
    "_FLOW_EXPLORER_BUNDLE_HTML_FILE_NAME",
    "original_html_file.html",
)
def test_open_flow_explorer_rf3(tmpdir, datadir):
    from robotframework_ls.impl.rf_model_builder import (
        DEFAULT_WARNING_MESSAGE,
        IS_ROBOT_FRAMEWORK_3,
    )

    return_path = (
        robotframework_ls_impl.RobotFrameworkLanguageServer._open_flow_explorer(
            MockRFLS(),
            {
                "currentFileUri": os.path.join(datadir, "default_simple.robot"),
                "htmlBundleFolderPath": tmpdir,
            },
        )
    )

    return_uri = urlparse(return_path["uri"])
    tmp_bundle_html_file_path = Path(url2pathname(return_uri.path))
    assert tmp_bundle_html_file_path.exists()

    file_contents = tmp_bundle_html_file_path.read_text()
    assert '<div id="root"></div>' in file_contents
    assert '<script id="data" type="application/json">' in file_contents
    assert "Main Implemented Keyword" in file_contents

    if IS_ROBOT_FRAMEWORK_3:
        assert return_path["warn"] == DEFAULT_WARNING_MESSAGE


@mock.patch("robotframework_ls.impl.rf_model_builder.RFModelBuilder.build")
def test_open_flow_explorer_raise_error(mockRFMbuild, tmpdir, datadir):
    original_file_name = "original_html_file.html"
    with mock.patch.object(
        robotframework_ls_impl,
        "_FLOW_EXPLORER_BUNDLE_HTML_FILE_NAME",
        original_file_name,
    ):
        mockRFMbuild.side_effect = RecursionError("Deep model raised issue.")

        return_path = (
            robotframework_ls_impl.RobotFrameworkLanguageServer._open_flow_explorer(
                None,
                {
                    "currentFileUri": os.path.join(datadir, "default_simple.robot"),
                    "htmlBundleFolderPath": tmpdir,
                },
            )
        )

        assert return_path["uri"] == None
        assert return_path["err"] == "Deep model raised issue."
