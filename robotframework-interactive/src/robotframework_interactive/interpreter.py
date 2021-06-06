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
from robotframework_interactive.callbacks import Callback
import traceback
from ast import NodeVisitor
from robotframework_interactive.robotfacade import RobotFrameworkFacade


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


class IOnReadyCall(object):
    def __call__(self, interpreter: "RobotFrameworkInterpreter"):
        pass


class RobotFrameworkInterpreter(object):
    def __init__(self):
        from robotframework_interactive import main_loop

        main_loop.MainLoopCallbackHolder.ON_MAIN_LOOP = self.interpreter_main_loop
        facade = RobotFrameworkFacade()
        get_model = facade.get_model
        TestSuite = facade.TestSuite

        model = get_model(
            """
*** Settings ***
Library    robotframework_interactive.main_loop    WITH NAME     MainLoop

*** Test Case ***
Default Test
    MainLoop.Interpreter Main Loop
"""
        )
        self._test_suite = TestSuite.from_model(model, name="Default test suite")
        self.on_stdout = Callback()
        self.on_stderr = Callback()
        self._stdout = _CustomStream(self.on_stdout)
        self._stderr = _CustomStream(self.on_stderr)
        self._on_main_loop = None

    def initialize(self, on_main_loop: IOnReadyCall):
        self._on_main_loop = on_main_loop
        import os

        stdout = self._stdout
        stderr = self._stderr
        options = dict(
            output=os.path.abspath("output.xml"), stdout=stdout, stderr=stderr
        )

        self._test_suite.run(**options)

    def interpreter_main_loop(self, *args, **kwargs):
        self._on_main_loop(self)

    def evaluate(self, code: str):
        try:
            self._evaluate(code)
        except Exception:
            s = traceback.format_exc()
            if s:
                for line in s.splitlines(keepends=True):
                    self.on_stderr(line)

    def _evaluate(self, code: str):
        # Compile AST
        from io import StringIO
        import os

        facade = RobotFrameworkFacade()
        get_model = facade.get_model
        TestSuite = facade.TestSuite
        TestDefaults = facade.TestDefaults
        SettingsBuilder = facade.SettingsBuilder
        EXECUTION_CONTEXTS = facade.EXECUTION_CONTEXTS
        SuiteBuilder = facade.SuiteBuilder

        model = get_model(
            StringIO(code),
            data_only=False,
            curdir=os.path.abspath(os.getcwd()).replace("\\", "\\\\"),
        )
        new_suite = TestSuite(name="Default test suite")
        defaults = TestDefaults()

        # Raise an error if there's anything wrong in the model that was parsed.
        _CustomErrorReporter(code).visit(model)

        SettingsBuilder(new_suite, defaults).visit(model)

        # Now, handle what was loaded in the settings builder.
        for new_import in new_suite.resource.imports:
            new_import.source = self._test_suite.source
            # Actually do the import
            current_context = EXECUTION_CONTEXTS.current
            namespace = current_context.namespace
            namespace._import(new_import)

        SuiteBuilder(new_suite, defaults).visit(model)
