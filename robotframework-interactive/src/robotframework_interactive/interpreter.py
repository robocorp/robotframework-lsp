"""
Some random notes on how Robot Framework does the running:

The main idea is that you create a TestSuite and run it.

Unfortunately, this isn't ideal for our use-case as the namespace is lost
during the running.

i.e.: in robot.running.suiterunner.SuiteRunner, in the `start_suite` method, a
Namespace is created and at that same place the imports for the TestSuite are
handled.

Afterwards, for each test it visits, it runs the needed setup/test/teardown loop.

But alas, we want to interactively add new library imports, resource imports,
keywords, so, the whole structure falls apart for the interpreter because the
visiting isn't really done per-statement, rather, the ast is collected and then
a bunch of internal structures are created and then the running is based on
those internal structures, not on the AST (probably a side-effect of having the
ast being added really late into Robot Framework and not from the start).

So, the approach being taken is the following:

1. Pre-create a test suite which will call a keyword where we'll pause to 
   actually execute the main loop.
   
2. In the main loop, collect the AST and then use the related builders to create
   the structure required to actually run, but instead of just blindly running it,
   verify what was actually loaded and dispatch accordingly (so, for instance,
   an import will use internal robot APIs to do the import -- and hopefully
   in the future when a usage is established, public APIs can be created in
   Robot Framework itself for this usage).

Previous work:

There is already a project which provides an interpreter:
    https://github.com/jupyter-xeus/robotframework-interpreter/blob/master/robotframework_interpreter/interpreter.py

    The approach used is that execute is done in blocks, so, it'll accept a full
    section and then execute it, copying back and forth the imports/variables/keywords
    between section evaluations.
"""
from robotframework_interactive.callbacks import Callback, CallbackWithReturn
import traceback
from ast import NodeVisitor
from robotframework_interactive.robotfacade import RobotFrameworkFacade
import sys
import os
from robotframework_interactive.protocols import (
    IOnReadyCall,
    EvaluateTextTypedDict,
    ActionResultDict,
)
import weakref
from typing import List, Dict, Any, Optional
from robocorp_ls_core.protocols import IConfig
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]


class IOnOutput(object):
    def __call__(self, s: str):
        pass


class _CustomStream(object):
    def __init__(self, on_output: Callback):
        self._on_output = on_output

    def write(self, s):
        self._on_output(s)

    def flush(self):
        pass

    def isatty(self):
        return False


class _CustomStdIn:
    def __init__(self, interpreter, original_stdin=sys.stdin):
        self._interpreter = weakref.ref(interpreter)
        try:
            self.encoding = sys.stdin.encoding
        except:
            pass
        self.original_stdin = original_stdin

        try:
            self.errors = (
                sys.stdin.errors
            )  # Who knew? sys streams have an errors attribute!
        except:
            # Not sure if it's available in all Python versions...
            pass

    def readline(self, *args, **kwargs):
        interpreter = self._interpreter()
        if interpreter is not None:
            interpreter.on_before_read()

        try:
            return self.original_stdin.readline(*args, **kwargs)
        except KeyboardInterrupt:
            raise  # Let KeyboardInterrupt go through
        except:
            return "\n"
        finally:
            if interpreter is not None:
                interpreter.on_after_read()

    def write(self, *args, **kwargs):
        pass  # not available _CustomStdIn (but it can be expected to be in the stream interface)

    def flush(self, *args, **kwargs):
        pass  # not available _CustomStdIn (but it can be expected to be in the stream interface)

    def read(self, *args, **kwargs):
        # in the interactive interpreter, a read and a readline are the same.
        return self.readline()

    def close(self, *args, **kwargs):
        pass  # expected in _CustomStdIn

    def __iter__(self):
        # _CustomStdIn would not be considered as Iterable in Python 3 without explicit `__iter__` implementation
        return self.original_stdin.__iter__()

    def __getattr__(self, item):
        # it's called if the attribute wasn't found
        if hasattr(self.original_stdin, item):
            return getattr(self.original_stdin, item)
        raise AttributeError("%s has no attribute %s" % (self.original_stdin, item))


class _CustomErrorReporter(NodeVisitor):
    def __init__(self, source):
        self.source = source

    def visit_Error(self, node):
        facade = RobotFrameworkFacade()
        Token = facade.Token
        DataError = facade.DataError

        # All errors raise here!
        fatal = node.get_token(Token.FATAL_ERROR)
        if fatal:
            raise DataError(self._format_message(fatal))
        for error in node.get_tokens(Token.ERROR):
            raise DataError(self._format_message(error))

    def _format_message(self, token):
        return "Error in file '%s' on line %s: %s" % (
            self.source,
            token.lineno,
            token.error,
        )


class RobotFrameworkInterpreter(object):
    def __init__(self, config: IConfig, workspace_root_path: Optional[str] = None):
        from robotframework_interactive import main_loop

        main_loop.MainLoopCallbackHolder.ON_MAIN_LOOP = self.interpreter_main_loop
        facade = RobotFrameworkFacade()
        TestSuite = facade.TestSuite

        self._config = config
        self._test_suite = TestSuite.from_file_system(
            os.path.join(os.path.dirname(__file__), "robot_interactive_console.robot")
        )
        self._workspace_root_path = workspace_root_path
        self.on_stdout = Callback()
        self.on_stderr = Callback()
        self.on_exception_handled = CallbackWithReturn()
        self._stdout = _CustomStream(self.on_stdout)
        self._stderr = _CustomStream(self.on_stderr)

        self._waiting_for_input = 0
        weak_self = weakref.ref(self)

        def before_read():
            s = weak_self()
            if s is not None:
                s._waiting_for_input += 1

        def after_read():
            s = weak_self()
            if s is not None:
                s._waiting_for_input -= 1

        self.on_before_read = Callback()
        self.on_before_read.register(before_read)

        self.on_after_read = Callback()
        self.on_after_read.register(after_read)

        self._on_main_loop = None

        self._settings_section_name_to_block_mode = {
            "SettingSection": ("*** Settings ***\n", ""),
            "VariableSection": ("*** Variables ***\n", ""),
            "TestCaseSection": ("*** Test Case ***\nDefault Task/Test\n", "    "),
            "KeywordSection": ("*** Keyword ***\n", ""),
            "CommentSection": ("*** Comment ***\n", ""),
        }
        self._last_section_name = "TestCaseSection"
        self._last_block_mode_and_indent = self._settings_section_name_to_block_mode[
            self._last_section_name
        ]
        # the section we're tracking -> section ast
        self._doc_parts = {
            "CommentSection": None,
            "SettingSection": None,
            "VariableSection": None,
            "TestCaseSection": None,
            "KeywordSection": None,
        }

        sys.stdin = _CustomStdIn(self)  # type:ignore

    @property
    def waiting_for_input(self):
        return bool(self._waiting_for_input)

    @property
    def full_doc(self) -> str:
        """
        :return:
            The full document as seen by the interpreter from what it was
            able to evaluate so far.

            Note that it should be logically consistent but not necessarily
            equal to what the user entered as statements.
        """
        return self._compute_full_doc()

    def _compute_full_doc(self, last_section_name=""):
        from robotframework_interactive.ast_to_code import ast_to_code

        full_doc = []
        sections = [
            "CommentSection",
            "SettingSection",
            "VariableSection",
            "KeywordSection",
            "TestCaseSection",
        ]
        if last_section_name:
            sections.remove(last_section_name)
            sections.append(last_section_name)

        for part in sections:
            part_as_ast = self._doc_parts[part]
            if part_as_ast:
                as_code = ast_to_code(part_as_ast).strip()
                if as_code:
                    full_doc.append(as_code)
        return ("\n".join(full_doc)).strip()

    def initialize(self, on_main_loop: IOnReadyCall):
        from robotframework_interactive.server.rf_interpreter_ls_config import (
            OPTION_ROBOT_VARIABLES,
        )
        from robotframework_interactive.server.rf_interpreter_ls_config import (
            OPTION_ROBOT_INTERACTIVE_CONSOLE_ARGUMENTS,
        )

        self._on_main_loop = on_main_loop  # type:ignore

        stdout = self._stdout
        stderr = self._stderr

        args: List[str] = self._config.get_setting(
            OPTION_ROBOT_INTERACTIVE_CONSOLE_ARGUMENTS, list, []
        )

        robot_variables = self._config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
        for key, val in robot_variables.items():
            args.append("--variable")
            args.append(f"{key}:{val}")

        facade = RobotFrameworkFacade()
        if self._workspace_root_path:
            output = os.path.join(
                self._workspace_root_path,
                "interactive_console_output.xml",
            )
        else:
            output = os.path.join(
                os.path.abspath("interactive_console_output.xml"),
            )
        options: Dict[str, Any] = dict(
            output=output,
        )
        try:
            options.update(facade.parse_arguments_options(args))
        except:
            log.exception(
                "Error parsing arguments starting interactive console: %s", args
            )

        log.info("Initializing robot framework interpreter with options: %s", options)

        options["stdout"] = stdout
        options["stderr"] = stderr

        self._test_suite.run(**options)

    def interpreter_main_loop(self, *args, **kwargs):
        self._on_main_loop(self)

    def compute_evaluate_text(
        self, code: str, target_type: str = "evaluate"
    ) -> EvaluateTextTypedDict:
        """
        :param target_type:
            'evaluate': means that the target is an evaluation with the given code.
                This implies that the current code must be changed to make sense
                in the given context.

            'completions': means that the target is a code-completion
                This implies that the current code must be changed to include
                all previous evaluation so that the code-completion contains
                the full information up to the current point.
        """
        ret: EvaluateTextTypedDict = {"prefix": "", "full_code": code, "indent": ""}

        if target_type == "completions":
            if code.strip().startswith("*"):
                # easy mode, just get the full doc and concatenate it with the code.
                prefix = self.full_doc + "\n"
                ret = {"prefix": prefix, "full_code": prefix + code, "indent": ""}
            else:
                # Ok, we need to see how the current code would fit in with the
                # existing code.
                last_section_name = self._last_section_name
                has_section = self._doc_parts.get(last_section_name) is not None
                if has_section:
                    prefix = self._compute_full_doc(last_section_name)
                    first_part, delimiter, last_line = prefix.rpartition("\n")
                    if delimiter:
                        whitespaces = []
                        for c in last_line:
                            if c in ("\t", " "):
                                whitespaces.append(c)
                            else:
                                break
                        indent = "".join(whitespaces)

                        if not indent:
                            # Corner case: the user entered:
                            # *** Tasks ***
                            # Task name
                            #
                            # but didn't add any keyword call -- we have to
                            # indent ourselves here.
                            _last_mode, indent = self._last_block_mode_and_indent
                            prefix = self.full_doc + "\n"
                            indented_code = indent + ("\n" + indent).join(
                                code.split("\n")
                            )
                            return {
                                "prefix": prefix,
                                "full_code": prefix + indented_code,
                                "indent": indent,
                            }

                        prefix = first_part + delimiter + last_line + "\n"
                        indented_code = indent + ("\n" + indent).join(code.split("\n"))
                        ret = {
                            "prefix": prefix,
                            "full_code": prefix + indented_code,
                            "indent": indent,
                        }

                    else:
                        ret = {
                            "prefix": prefix,
                            "full_code": prefix + "\n" + code,
                            "indent": "",
                        }
                else:
                    # There's no entry for this kind of section so far, so, we
                    # need to get the full block mode.
                    last_mode, indent = self._last_block_mode_and_indent
                    prefix = self.full_doc + "\n" + last_mode
                    indented_code = indent + ("\n" + indent).join(code.split("\n"))
                    ret = {
                        "prefix": prefix,
                        "full_code": prefix + indented_code,
                        "indent": indent,
                    }

        else:
            if not code.strip().startswith("*"):
                last_mode, indent = self._last_block_mode_and_indent
                indented_code = ("\n" + indent).join(code.split("\n"))
                ret = {
                    "prefix": last_mode,
                    "indent": indent,
                    "full_code": last_mode + indent + indented_code,
                }

        return ret

    def evaluate(self, code: str) -> ActionResultDict:
        original_stdout = sys.__stdout__
        original_stderr = sys.__stderr__
        try:
            # When writing to the console, RF uses sys.__stdout__, so, we
            # need to hijack it too...
            sys.__stdout__ = self._stdout  # type:ignore
            sys.__stderr__ = self._stderr  # type:ignore

            code = code.replace("\r\n", "\n").replace("\r", "\n")
            return self._evaluate(code)
        except Exception as e:
            if not self.on_exception_handled(e):
                # If it's not handled by some client, print it to stderr.
                s = traceback.format_exc()
                if s:
                    for line in s.splitlines(keepends=True):
                        self.on_stderr(line)
            return {
                "success": False,
                "message": f"Error while evaluating: {e}",
                "result": None,
            }
        finally:
            setattr(sys, "__stdout__", original_stdout)
            setattr(sys, "__stderr__", original_stderr)

    def _evaluate(self, code: str) -> ActionResultDict:
        # Compile AST
        from io import StringIO
        from robot.api import Token

        facade = RobotFrameworkFacade()
        get_model = facade.get_model
        TestSuite = facade.TestSuite
        TestDefaults = facade.TestDefaults
        SettingsBuilder = facade.SettingsBuilder
        EXECUTION_CONTEXTS = facade.EXECUTION_CONTEXTS
        SuiteBuilder = facade.SuiteBuilder
        code = self.compute_evaluate_text(code)["full_code"]

        model = get_model(
            StringIO(code),
            data_only=False,
            curdir=os.path.abspath(os.getcwd()).replace("\\", "\\\\"),
        )

        if not model.sections:
            msg = "Unable to interpret: no sections found."
            self.on_stderr(msg)
            return {
                "success": False,
                "message": f"Error while evaluating: {msg}",
                "result": None,
            }

        # Raise an error if there's anything wrong in the model that was parsed.
        _CustomErrorReporter(code).visit(model)

        # Initially it was engineered so that typing *** Settings *** would enter
        # *** Settings *** mode, but this idea was abandoned (it's implementation
        # is still here as we may want to revisit it, but it has some issues
        # in how to compute the full doc for code-completion, so, the default
        # section is always a test-case section now).
        #
        # last_section = model.sections[-1]
        # last_section_name = last_section.__class__.__name__
        # last_section_name = "TestCaseSection"
        # block_mode = self._settings_section_name_to_block_mode.get(last_section_name)
        # if block_mode is None:
        #     self.on_stderr(f"Unable to find block mode for: {last_section_name}")
        #
        # else:
        #     self._last_block_mode_and_indent = block_mode
        #     self._last_section_name = last_section_name

        new_suite = TestSuite(name="Default test suite")
        defaults = TestDefaults()

        SettingsBuilder(new_suite, defaults).visit(model)
        SuiteBuilder(new_suite, defaults).visit(model)

        # ---------------------- handle what was loaded in the settings builder.
        current_context = EXECUTION_CONTEXTS.current
        namespace = current_context.namespace
        source = os.path.join(
            os.path.abspath(os.getcwd()), "in_memory_interpreter.robot"
        )
        for new_import in new_suite.resource.imports:
            self._set_source(new_import, source)
            # Actually do the import (library, resource, variable)
            namespace._import(new_import)

        if new_suite.resource.variables:
            # Handle variables defined in the current test.
            for variable in new_suite.resource.variables:
                self._set_source(variable, source)

            namespace.variables.set_from_variable_table(new_suite.resource.variables)

        if new_suite.resource.keywords:
            # It'd be really nice to have a better API for this...
            user_keywords = namespace._kw_store.user_keywords
            for kw in new_suite.resource.keywords:
                try:
                    kw.actual_source = source
                except AttributeError:
                    kw.parent.source = source
                handler = user_keywords._create_handler(kw)

                embedded = isinstance(handler, facade.EmbeddedArgumentsHandler)
                if not embedded:
                    if handler.name in user_keywords.handlers._normal:
                        del user_keywords.handlers._normal[handler.name]
                user_keywords.handlers.add(handler, embedded)

        # --------------------------------------- Actually run any test content.
        last_result = None
        for test in new_suite.tests:
            context = EXECUTION_CONTEXTS.current
            last_result = facade.run_test_body(context, test, model)

        if len(new_suite.tests) == 1 and last_result is not None:
            self._stdout.write(f"{last_result}\n")

        # Now, update our representation of the document to include what the
        # user just entered.
        for section in model.sections:
            section_name = section.__class__.__name__
            if section.body:
                if section_name not in self._doc_parts:
                    continue

                current = self._doc_parts[section_name]
                if not current:
                    add = True
                    if section.__class__.__name__ == "TestCaseSection" and (
                        not section.body
                        or (len(section.body) == 1 and not section.body[0].body)
                    ):
                        add = False
                    if add:
                        current = self._doc_parts[section_name] = section
                else:
                    if current.__class__.__name__ == "TestCaseSection":
                        current = current.body[-1]
                        for test_case in section.body:
                            current.body.extend(test_case.body)
                    else:
                        current.body.extend(section.body)

                if current is not None:
                    # Make sure that there is a '\n' as the last EOL.
                    last_in_body = current.body[-1]
                    while not hasattr(last_in_body, "tokens"):
                        last_in_body = last_in_body.body[-1]
                    tokens = last_in_body.tokens
                    last_token = tokens[-1]
                    found_new_line = False
                    if last_token.type == Token.EOL:
                        if not last_token.value:
                            last_token.value = "\n"
                            found_new_line = True
                    if not found_new_line:
                        last_in_body.tokens += (Token("EOL", "\n"),)

        return {"success": True, "message": None, "result": None}

    def _set_source(self, element, source):
        try:
            element.source = source
        except AttributeError:
            element.parent.source = source
