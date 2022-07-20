import json
import tempfile
import pytest
import os
from pathlib import Path

from robotframework_ls_tests.fixtures import (
    DEFAULT_BOT_SIMPLE_FILE,
    DEFAULT_FLOW_EXPLORER_BUNDLE_HTML,
    DEFAULT_JSON_BOT,
    DEFAULT_JSON_BOT_INFINITE_LOOP,
)
from robotframework_ls.impl.rf_model_builder import RFModelBuilder

from robotframework_ls import robotframework_ls_impl as rfli


def test_recursive_exploration():
    model = json.loads(DEFAULT_JSON_BOT)
    task = model["tasks"][0]
    task["body"] = RFModelBuilder("test")._recursive_exploration(model, task)

    assert len(task["body"]) > 0
    assert task["body"][0]["name"] == "Main Implemented Keyword"
    assert len(task["body"][0]["body"]) > 0

    assert task["body"][0]["body"][0]["name"] == "Comment 1"


def test_recursive_exploration_infinite_fail():
    model = json.loads(DEFAULT_JSON_BOT_INFINITE_LOOP)
    task = model["tasks"][0]
    with pytest.raises(RecursionError):
        task["body"] = RFModelBuilder("test")._recursive_exploration(model, task)

    assert len(task["body"]) > 0
    assert task["body"][0]["name"] == "Main Implemented Keyword"
    assert len(task["body"][0]["body"]) == 0


def test_build_deep_model():
    model = json.loads(DEFAULT_JSON_BOT)
    model = RFModelBuilder("test")._build_deep_model(model)
    task = model["tasks"][0]

    assert len(task["body"]) > 0
    assert task["body"][0]["name"] == "Main Implemented Keyword"
    assert len(task["body"][0]["body"]) > 0

    assert task["body"][0]["body"][0]["name"] == "Comment 1"


def test_build_deep_model_infinite_fail():
    model = json.loads(DEFAULT_JSON_BOT_INFINITE_LOOP)
    task = model["tasks"][0]
    with pytest.raises(RecursionError):
        RFModelBuilder("test")._build_deep_model(model)

    assert len(task["body"]) > 0
    assert task["body"][0]["name"] == "Main Implemented Keyword"
    assert len(task["body"][0]["body"]) == 0


def test_open_flow_explorer():
    with tempfile.TemporaryDirectory() as dir_name:
        original_file_name = "original_html_file.html"
        robot_bundle_html_file_path = Path(os.path.join(dir_name, original_file_name))
        rfli._FLOW_EXPLORER_BUNDLE_HTML_FILE_NAME = original_file_name
        robot_bundle_html_file_path.write_text(DEFAULT_FLOW_EXPLORER_BUNDLE_HTML)

        robot_file_path = Path(os.path.join(dir_name, "original_robot.robot"))
        robot_file_path.write_text(DEFAULT_BOT_SIMPLE_FILE)

        return_path = rfli.RobotFrameworkLanguageServer._open_flow_explorer(
            None,
            {
                "currentFileUri": robot_file_path,
                "htmlBundleFolderPath": dir_name,
            },
        )

        tmp_bundle_html_file_name = "tmp_original_html_file.html"
        tmp_bundle_html_file_path = Path(
            os.path.join(dir_name, tmp_bundle_html_file_name)
        )
        assert tmp_bundle_html_file_path.exists()
        assert return_path == tmp_bundle_html_file_path.as_uri()

        file_contents = tmp_bundle_html_file_path.read_text()
        assert '<div id="root"></div>' in file_contents
        assert '<script id="data" type="application/json">' in file_contents
        assert "Main Implemented Keyword" in file_contents


def test_open_flow_explorer_raise_error():
    with tempfile.TemporaryDirectory() as dir_name:
        original_file_name = "original_html_file.html"
        robot_bundle_html_file_path = Path(os.path.join(dir_name, original_file_name))
        robot_bundle_html_file_path.write_text(DEFAULT_FLOW_EXPLORER_BUNDLE_HTML)

        robot_file_path = Path(os.path.join(dir_name, "original_robot.robot"))
        robot_file_path.write_text(DEFAULT_BOT_SIMPLE_FILE)

        class Mock_RFModelBuilder(RFModelBuilder):
            def build(self):
                raise RecursionError("Deep model raised issue.")

        rfli._FLOW_EXPLORER_BUNDLE_HTML_FILE_NAME = original_file_name
        rfli.RFModelBuilder = Mock_RFModelBuilder
        return_path = rfli.RobotFrameworkLanguageServer._open_flow_explorer(
            None,
            {
                "currentFileUri": robot_file_path,
                "htmlBundleFolderPath": dir_name,
            },
        )

        assert return_path == None
