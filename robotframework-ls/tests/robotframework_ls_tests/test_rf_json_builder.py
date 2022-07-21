import json
import tempfile
import mock
import pytest
import os
from pathlib import Path

from robotframework_ls.impl.rf_model_builder import (
    DEFAULT_WARNING_MESSAGE,
    IS_ROBOT_FRAMEWORK_3,
    RFModelBuilder,
)
from robotframework_ls import robotframework_ls_impl as rfli
from urllib.parse import urlparse

DEFAULT_JSON_BOT = """{
  "type": "suite",
  "name": "Tasks",
  "source": "tasks.robot",
  "doc": "",
  "setup": null,
  "teardown": null,
  "keywords": [
    {
      "type": "user-keyword",
      "name": "Main Implemented Keyword",
      "doc": "",
      "tags": [],
      "args": [],
      "returns": [],
      "timeout": null,
      "error": null,
      "lineno": 18,
      "body": [
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Comment 1",
          "assign": [],
          "args": ["This is something grand"],
          "body": []
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Comment",
          "assign": [],
          "args": ["This is something grand"],
          "body": []
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Comment",
          "assign": [],
          "args": ["New Keyword"],
          "body": []
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Second Implemented Keyword",
          "assign": [],
          "args": [],
          "body": []
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Third Implemented Keyword",
          "assign": [],
          "args": [],
          "body": []
        }
      ]
    },
    {
      "type": "user-keyword",
      "name": "Second Implemented Keyword",
      "doc": "",
      "tags": [],
      "args": [],
      "returns": [],
      "timeout": null,
      "error": null,
      "lineno": 24,
      "body": [
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Comment",
          "assign": [],
          "args": ["This is something grand"],
          "body": []
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Third Implemented Keyword",
          "assign": [],
          "args": [],
          "body": []
        }
      ]
    },
    {
      "type": "user-keyword",
      "name": "Third Implemented Keyword",
      "doc": "",
      "tags": [],
      "args": [],
      "returns": [],
      "timeout": null,
      "error": null,
      "lineno": 24,
      "body": [
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Comment",
          "assign": [],
          "args": ["This is something grand"],
          "body": []
        }
      ]
    }
  ],
  "variables": [],
  "imports": [
    {
      "type": "import",
      "subtype": "Library",
      "name": "RPA.Browser.Selenium",
      "args": [],
      "alias": null,
      "lineno": 2
    }
  ],
  "tasks": [
    {
      "type": "task",
      "name": "Main Task",
      "doc": "",
      "setup": null,
      "teardown": null,
      "body": [
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Main Implemented Keyword",
          "assign": [],
          "args": [],
          "body": []
        },
        {
          "type": "if",
          "body": [
            {
              "type": "if-branch",
              "condition": "${TRUE}",
              "body": [
                {
                  "type": "keyword",
                  "subtype": "KEYWORD",
                  "name": "Main Implemented Keyword",
                  "assign": [],
                  "args": [],
                  "body": []
                },
                {
                  "type": "keyword",
                  "subtype": "KEYWORD",
                  "name": "Comment",
                  "assign": [],
                  "args": ["This is something grand"],
                  "body": []
                }
              ]
            },
            {
              "type": "else-branch",
              "body": [
                {
                  "type": "keyword",
                  "subtype": "KEYWORD",
                  "name": "Comment",
                  "assign": [],
                  "args": ["This is something grand"],
                  "body": []
                },
                {
                  "type": "keyword",
                  "subtype": "KEYWORD",
                  "name": "Third Implemented Keyword",
                  "assign": [],
                  "args": [],
                  "body": []
                }
              ]
            }
          ]
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Open available browser",
          "assign": [],
          "args": ["https://example.com"],
          "body": []
        }
      ]
    }
  ],
  "suites": []
}

"""

DEFAULT_JSON_BOT_INFINITE_LOOP = """
{
  "type": "suite",
  "name": "Tasks",
  "source": "tasks.robot",
  "doc": "",
  "setup": null,
  "teardown": null,
  "keywords": [
    {
      "type": "user-keyword",
      "name": "Main Implemented Keyword",
      "doc": "",
      "tags": [],
      "args": [],
      "returns": [],
      "timeout": null,
      "error": null,
      "lineno": 18,
      "body": [
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Comment",
          "assign": [],
          "args": ["This is something grand"],
          "body": []
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Comment",
          "assign": [],
          "args": ["This is something grand"],
          "body": []
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Comment",
          "assign": [],
          "args": ["New Keyword"],
          "body": []
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Second Implemented Keyword",
          "assign": [],
          "args": [],
          "body": []
        }
      ]
    },
    {
      "type": "user-keyword",
      "name": "Second Implemented Keyword",
      "doc": "",
      "tags": [],
      "args": [],
      "returns": [],
      "timeout": null,
      "error": null,
      "lineno": 24,
      "body": [
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Comment",
          "assign": [],
          "args": ["This is something grand"],
          "body": []
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Main Implemented Keyword",
          "assign": [],
          "args": [],
          "body": []
        }
      ]
    }
  ],
  "variables": [],
  "imports": [
    {
      "type": "import",
      "subtype": "Library",
      "name": "RPA.Browser.Selenium",
      "args": [],
      "alias": null,
      "lineno": 2
    }
  ],
  "tasks": [
    {
      "type": "task",
      "name": "Main Task",
      "doc": "",
      "setup": null,
      "teardown": null,
      "body": [
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Main Implemented Keyword",
          "assign": [],
          "args": [],
          "body": []
        },
        {
          "type": "if",
          "body": [
            {
              "type": "if-branch",
              "condition": "${TRUE}",
              "body": [
                {
                  "type": "keyword",
                  "subtype": "KEYWORD",
                  "name": "Main Implemented Keyword",
                  "assign": [],
                  "args": [],
                  "body": []
                },
                {
                  "type": "keyword",
                  "subtype": "KEYWORD",
                  "name": "Comment",
                  "assign": [],
                  "args": ["This is something grand"],
                  "body": []
                }
              ]
            },
            {
              "type": "else-branch",
              "body": [
                {
                  "type": "keyword",
                  "subtype": "KEYWORD",
                  "name": "Comment",
                  "assign": [],
                  "args": ["This is something grand"],
                  "body": []
                }
              ]
            }
          ]
        },
        {
          "type": "keyword",
          "subtype": "KEYWORD",
          "name": "Open available browser",
          "assign": [],
          "args": ["https://example.com"],
          "body": []
        }
      ]
    }
  ],
  "suites": []
}
"""

DEFAULT_BOT_SIMPLE_FILE = """
*** Settings ***
Library     RPA.Browser.Selenium


*** Tasks ***
Main Task
    Main Implemented Keyword
    if    ${TRUE}
        Main Implemented Keyword
        Comment    This is something grand
    else
        Comment    This is something grand
        Third Implemented Keyword
    end
    Open available browser    https://example.com

*** Keywords ***
Main Implemented Keyword
    Comment    This is something grand
    Comment    This is something grand
    Comment    New Keyword
    Second Implemented Keyword

Second Implemented Keyword
    Comment    This is something grand
    Open available browser    https://example.com
    Third Implemented Keyword

Third Implemented Keyword
    Comment    This is something grand

"""

DEFAULT_RF3_BOT = """
*** Settings ***
Library     RPA.Browser.Selenium

*** Variables ***
${LOGIN_STR}      raspberrypi login:
${SERIAL_PORT}    /dev/ttyUSB0
${RPI_IP}         10.0.1.22
${USERNAME}       pi
${PASSWORD}       raspberry
${PROMPT}         pi@raspberrypi:

*** Tasks ***
Main Task
    Main Implemented Keyword
    IF    ${TRUE}
        Main Implemented Keyword
        Comment    This is something grand
    ELSE
        Comment    This is something grand
        Third Implemented Keyword
    END
    Open available browser    https://example.com
    Run Keyword If  '${color}' == 'Red' or '${color}' == 'Blue' or '${color}' == 'Pink'  log to console
    sleep    ${Delay}
    FOR	${var}	IN	@{VALUES}
      Run Keyword If	'${var}' == 'CONTINUE'	Continue For Loop
      Do Something	${var}
      sleep    ${Delay}
    END


*** Keywords ***
Main Implemented Keyword
    Comment    This is something grand
    Comment    This is something grand
    Comment    New Keyword
    Second Implemented Keyword

Second Implemented Keyword
    Comment    This is something grand
    Open available browser    https://example.com
    Third Implemented Keyword

Third Implemented Keyword
    Comment    This is something grand

"""

DEFAULT_FLOW_EXPLORER_BUNDLE_HTML = """
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1,shrink-to-fit=no" />
        <title>Robocorp - Robot Flow Explorer</title>
        <script id="data" type="application/json"></script>
        <link rel="icon" href="favicon.png" />
    </head>
    <body>
        <noscript>Robot Visualization requires JavaScript</noscript>
        <div id="root"></div>
        <script defer="defer" src="index_bundle.js"></script>
    </body>
</html>
"""


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

        return_uri = urlparse(return_path["uri"])
        tmp_bundle_html_file_path = Path(
            os.path.join(return_uri.netloc, return_uri.path)
        )
        assert tmp_bundle_html_file_path.exists()

        file_contents = tmp_bundle_html_file_path.read_text()
        assert '<div id="root"></div>' in file_contents
        assert '<script id="data" type="application/json">' in file_contents
        assert "Main Implemented Keyword" in file_contents


def test_open_flow_explorer_rf3():
    with tempfile.TemporaryDirectory() as dir_name:
        original_file_name = "original_html_file.html"
        robot_bundle_html_file_path = Path(os.path.join(dir_name, original_file_name))
        rfli._FLOW_EXPLORER_BUNDLE_HTML_FILE_NAME = original_file_name
        robot_bundle_html_file_path.write_text(DEFAULT_FLOW_EXPLORER_BUNDLE_HTML)

        robot_file_path = Path(os.path.join(dir_name, "original_robot.robot"))
        robot_file_path.write_text(DEFAULT_RF3_BOT)

        return_path = rfli.RobotFrameworkLanguageServer._open_flow_explorer(
            None,
            {
                "currentFileUri": robot_file_path,
                "htmlBundleFolderPath": dir_name,
            },
        )

        return_uri = urlparse(return_path["uri"])
        tmp_bundle_html_file_path = Path(
            os.path.join(return_uri.netloc, return_uri.path)
        )
        assert tmp_bundle_html_file_path.exists()

        file_contents = tmp_bundle_html_file_path.read_text()
        assert '<div id="root"></div>' in file_contents
        assert '<script id="data" type="application/json">' in file_contents
        assert "Main Implemented Keyword" in file_contents

        if IS_ROBOT_FRAMEWORK_3:
            assert return_path["warn"] == DEFAULT_WARNING_MESSAGE


@mock.patch("robotframework_ls.impl.rf_model_builder.RFModelBuilder")
def test_open_flow_explorer_raise_error(mockRFModelBuilder):
    with tempfile.TemporaryDirectory() as dir_name:
        original_file_name = "original_html_file.html"
        robot_bundle_html_file_path = Path(os.path.join(dir_name, original_file_name))
        robot_bundle_html_file_path.write_text(DEFAULT_FLOW_EXPLORER_BUNDLE_HTML)

        robot_file_path = Path(os.path.join(dir_name, "original_robot.robot"))
        robot_file_path.write_text(DEFAULT_BOT_SIMPLE_FILE)

        # class Mock_RFModelBuilder(RFModelBuilder):
        #     def build(self):
        #         raise RecursionError("Deep model raised issue.")

        rfli._FLOW_EXPLORER_BUNDLE_HTML_FILE_NAME = original_file_name
        # rfli.RFModelBuilder = Mock_RFModelBuilder

        mockRFModelBuilder.side_effect = RecursionError("Deep model raised issue.")

        return_path = rfli.RobotFrameworkLanguageServer._open_flow_explorer(
            None,
            {
                "currentFileUri": robot_file_path,
                "htmlBundleFolderPath": dir_name,
            },
        )

        assert return_path["uri"] == None
        assert return_path["err"] == "Deep model raised issue."
