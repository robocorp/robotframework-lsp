############################################################################
# TODO: Review the implementation here.
# Most of the implementation here is a mixture of different implementations
# that were done along the way of translating the module to JSON understandable
# data. A lot more content is missing.
# This is a lightweight version of the builder.
############################################################################

import os
from typing import Dict
from robot.api import SuiteVisitor
from robot.running.builder.builders import SuiteStructureParser as _SuiteStructureParser
from robot.running.builder.parsers import NoInitFileDirectoryParser
from robot.parsing import get_init_model, get_model, get_resource_model
from robot.errors import DataError  # type: ignore
from robot.running.builder.parsers import BaseParser, format_name
from robot.running.builder.transformers import (
    ResourceBuilder,
    SettingsBuilder,
    SuiteBuilder,
)
from robot.running.model import ResourceFile, TestSuite
from robot.utils import FileReader, read_rest_data  # type: ignore
from robocorp_ls_core.robotframework_log import get_logger
from robot.parsing import SuiteStructureBuilder

from robotframework_ls.impl.robot_version import get_robot_major_version

# We don't even support version 2, so, this is ok.
IS_ROBOT_FRAMEWORK_3 = get_robot_major_version() == 3
IS_ROBOT_FRAMEWORK_5_ONWARDS = get_robot_major_version() >= 5

DEFAULT_WARNING_MESSAGE = """
Detected a Robot Framework incompatible version.
Be advised that the Robot Flow Explorer might not render as expected.
For proper results please upgrade to the latest version.
"""

try:
    from robot.running.builder.settings import Defaults as TestDefaults
except:
    from robot.running.builder.testsettings import TestDefaults


log = get_logger(__name__)


class Error:
    source: str
    lineno: int
    error: str
    fatal: bool

    def __init__(self, source="", lineno=0, error="", fatal=False) -> None:
        self.source = source
        self.lineno = lineno
        self.error = error
        self.fatal = fatal


class BodyParser(SuiteVisitor):
    def __init__(self):
        self.stack = []

    @property
    def current(self):
        return self.stack[-1] if self.stack else None

    def start_keyword(self, keyword):
        model = {
            "type": "keyword",
            "subtype": keyword.type,
            "name": keyword.name,
            "assign": keyword.assign,
            "args": keyword.args,
            "body": [],
        }

        if keyword.type.lower() == "keyword":
            self.current["body"].append(model)
        elif keyword.type.lower() == "setup":
            self.current["setup"] = model
        elif keyword.type.lower() == "teardown":
            self.current["teardown"] = model
        elif IS_ROBOT_FRAMEWORK_3:
            if keyword.type.lower() == "for":
                self.start_for(keyword)
            else:
                self.current["body"].append(model)
        else:
            raise RuntimeError(f"Unhandled keyword type: {keyword.type}")

        self.stack.append(model)
        return True

    def end_keyword(self, keyword):
        self.stack.pop()

    def start_for(self, for_):
        model = {
            "type": "for",
            "flavor": for_.flavor,
            "variables": for_.variables,
            "values": for_.values,
            "body": [],
        }

        self.current["body"].append(model)
        self.stack.append(model)

        if IS_ROBOT_FRAMEWORK_3:
            for kw in for_.keywords.all:
                self.start_keyword(kw)
                self.end_keyword(kw)

    def end_for(self, for_):
        self.stack.pop()

    def start_if(self, if_):
        model = {
            "type": "if",
            "body": [],
        }

        self.current["body"].append(model)
        self.stack.append(model)

    def end_if(self, if_):
        self.stack.pop()

    def start_if_branch(self, branch):
        if branch.type == "IF":
            model = {
                "type": "if-branch",
                "condition": branch.condition,
                "body": [],
            }
        elif branch.type == "ELSE IF":
            model = {
                "type": "else-if-branch",
                "condition": branch.condition,
                "body": [],
            }
        elif branch.type == "ELSE":
            model = {
                "type": "else-branch",
                "body": [],
            }
        else:
            raise RuntimeError(f"Unknown branch type: {branch.type}")

        self.current["body"].append(model)
        self.stack.append(model)

    def end_if_branch(self, branch):
        self.stack.pop()

    def start_try(self, try_):
        model = {
            "type": "try",
            "body": [],
        }
        self.current["body"].append(model)
        self.stack.append(model)

    def end_try(self, try_):
        self.stack.pop()

    def start_try_branch(self, branch):
        if branch.type == "TRY":
            model = {
                "type": "try-branch",
                "body": [],
            }
        elif branch.type == "EXCEPT":
            model = {
                "type": "except-branch",
                "body": [],
            }
        elif branch.type == "FINALLY":
            model = {
                "type": "finally-branch",
                "body": [],
            }
        else:
            raise RuntimeError(f"Unknown branch type: {branch.type}")
        self.current["body"].append(model)
        self.stack.append(model)

    def end_try_branch(self, branch):
        self.stack.pop()

    def start_while(self, while_):
        model = {
            "type": "while",
            "flavor": while_.flavor,
            "variables": while_.variables,
            "values": while_.values,
            "body": [],
        }

        self.current["body"].append(model)
        self.stack.append(model)

    def end_while(self, while_):
        self.stack.pop()


class KeywordModelParser(BodyParser):
    def __init__(self):
        super().__init__()
        self.model = None

    def parse(self, keyword):
        model_keywords = keyword.keywords
        self.model = {
            "type": "user-keyword",
            "name": keyword.name,
            "doc": keyword.doc,
            "tags": [str(tag) for tag in keyword.tags],
            "args": keyword.args,
            "returns": keyword.return_,
            "timeout": keyword.timeout,
            "error": keyword.error if not IS_ROBOT_FRAMEWORK_3 else [],
            "lineno": keyword.lineno,
            "body": [],
        }

        self.stack.append(self.model)

        if not IS_ROBOT_FRAMEWORK_3:
            keyword.body.visit(self)
            keyword.teardown.visit(self)
        else:
            keyword.keywords.visit(self)

        return self.model


class SuiteModelParser(BodyParser):
    def __init__(self):
        super().__init__()
        self.model = None

    def parse(self, suite):
        suite.visit(self)
        if not self.model:
            raise ValueError("Failed to parse any suite model")

        return self.model

    def start_suite(self, suite):
        if hasattr(suite, "resource"):
            # TODO: Figure this out
            variables = [str(var) for var in suite.resource.variables]
            keywords = [
                KeywordModelParser().parse(kw) for kw in suite.resource.keywords
            ]
            imports = [
                {
                    "type": "import",
                    "subtype": imp.type,
                    "name": imp.name,
                    "args": imp.args,
                    "alias": imp.alias,
                    "lineno": imp.lineno,
                }
                for imp in suite.resource.imports
            ]
        else:
            variables = []
            keywords = []
            imports = []

        model = {
            "type": "suite",
            "name": suite.name,
            "source": suite.source,
            "doc": suite.doc,
            "setup": None,
            "teardown": None,
            "keywords": keywords,
            "variables": variables,
            "imports": imports,
            "tasks": [],
            "suites": [],
        }

        if self.model is None:
            self.model = model
        else:
            self.current["suites"].append(model)

        self.stack.append(model)

    def end_suite(self, suite):
        self.stack.pop()

    def start_test(self, test):
        model = {
            "type": "task",
            "name": test.name,
            "doc": test.doc,
            "setup": None,
            "teardown": None,
            "body": [],
        }

        self.current["tasks"].append(model)
        self.stack.append(model)

    def end_test(self, test):
        self.stack.pop()


class SuiteStructureParser(_SuiteStructureParser):
    def __init__(self, *args, **kwargs):
        self._errors = {}

        kwargs.setdefault("included_extensions", ("robot",))
        if IS_ROBOT_FRAMEWORK_5_ONWARDS:
            ssp = _SuiteStructureParser(*args, **kwargs)
            self.rpa = ssp.rpa
            self._rpa_given = ssp._rpa_given
            self.suite = ssp.suite
            self._stack = ssp._stack
            self.parsers = ssp.parsers
        else:
            super().__init__(included_extensions=("robot",))

    def _get_parsers(self, extensions, process_curdir):
        del process_curdir

        robot_parser = RobotParser(errors=self._errors)
        rest_parser = RestParser(errors=self._errors)

        parsers = {
            None: NoInitFileDirectoryParser(),
            "robot": robot_parser,
            "rst": rest_parser,
            "rest": rest_parser,
        }

        for ext in extensions:
            if ext not in parsers:
                parsers[ext] = robot_parser

        return parsers

    def parse(self, structure):
        structure.visit(self)
        if self.suite is not None:
            self.suite.rpa = self.rpa

        return self.suite, self._errors


class RobotParser(BaseParser):
    def __init__(self, errors=None):
        self._errors = errors if errors is not None else {}

    def parse_init_file(self, source, defaults=None) -> TestSuite:
        directory = os.path.dirname(source)
        suite = TestSuite(name=format_name(directory), source=source)
        return self._build(suite, source, defaults, model_parser=get_init_model)

    def parse_suite_file(self, source, defaults=None) -> TestSuite:
        suite = TestSuite(name=format_name(source), source=source)
        return self._build(suite, source, defaults)

    def _build(self, suite, source, defaults, model=None, model_parser=get_model):
        if defaults is None:
            defaults = TestDefaults()

        if model is None:
            model = model_parser(self._get_source(source), data_only=True)

        errors = self._errors.setdefault(source, [])

        try:
            # TODO: Use custom transformers instead of running model visitor
            SettingsBuilder(suite, defaults).visit(model)
            SuiteBuilder(suite, defaults).visit(model)
            suite.rpa = self._get_rpa_mode(model)
        except DataError as err:
            error = Error(source=source, error=str(err), fatal=True)
            errors.append(error)

        return suite

    def _get_rpa_mode(self, data) -> bool:
        if not data:
            return False

        tasks = [s.tasks for s in data.sections if hasattr(s, "tasks")]
        if all(tasks) or not any(tasks):
            return all(tasks)

        raise DataError("One file cannot have both tests and tasks")

    def parse_resource_file(self, source) -> ResourceFile:
        resource = ResourceFile(source=source)
        model = get_resource_model(source=self._get_source(source), data_only=True)

        errors = self._errors.setdefault(source, [])

        try:
            ResourceBuilder(resource).visit(model)
        except DataError as err:
            error = Error(source=source, error=err, fatal=True)
            errors.append(error)

        return resource

    def _get_source(self, source):
        return source


class RestParser(RobotParser):
    def _get_source(self, source):
        with FileReader(source) as reader:
            return read_rest_data(reader)


class RFModelBuilder:
    def __init__(self, robot_file_path, debug=False) -> None:
        self.robot_file_path = robot_file_path
        self.debug = debug
        if not self.robot_file_path:
            raise ValueError("JSONModel needs a valid .robot file path")

    def _print_element(self, element, msg=None, level=1):
        if not self.debug:
            return

        def prefix(x):
            return "-" * x + " "

        if "name" in element:
            print(
                prefix(level) + (msg if msg is not None else "") + " " + element["name"]
            )
        if "body" in element:
            for elem in element["body"]:
                if "name" in elem:
                    print(prefix(level + 1) + " HAS: " + elem["name"])

    @staticmethod
    def _find_element_by_name(collection, name):
        for elem in collection:
            if "name" in elem and elem["name"] == name:
                return elem
        return {}

    def _recursive_exploration(self, model, parent):
        self._print_element(parent, "Parent:")
        if parent and "body" in parent and len(parent["body"]) > 0:
            for child in parent["body"]:
                self._print_element(child, "Child:", 2)
                if (
                    "body" in child
                    and len(child["body"]) == 0
                    and "type" in child
                    and str(child["type"]).lower() == "keyword"
                ):
                    user_keyword = self._find_element_by_name(
                        model["keywords"], child["name"]
                    )
                    if len(user_keyword) > 0:
                        self._print_element(user_keyword, "Found UK:", 2)
                        child["body"] = self._recursive_exploration(model, user_keyword)
                    self._print_element(child, "Continue 1...", 2)
                    continue
                child["body"] = self._recursive_exploration(model, child)
                self._print_element(child, "Continue 2...", 2)
                continue
        self._print_element(parent, "Return parent body = ")
        return parent["body"]

    def _build_deep_model(self, model):
        if "tasks" in model:
            for task in model["tasks"]:
                task["body"] = self._recursive_exploration(model, task)
        if "keywords" in model:
            for keyword in model["keywords"]:
                keyword["body"] = self._recursive_exploration(model, keyword)
        return model

    def build(self) -> Dict:
        builder = SuiteStructureBuilder()
        structure = builder.build(paths=[self.robot_file_path])

        parser = SuiteStructureParser()
        suite, _ = parser.parse(structure)

        transformer = SuiteModelParser()
        model = transformer.parse(suite)

        return self._build_deep_model(model)
