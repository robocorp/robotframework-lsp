class Token:
    SETTING_HEADER: str
    VARIABLE_HEADER: str
    TESTCASE_HEADER: str
    TASK_HEADER: str  # Note: not available on ALL RF versions (added in 5.1)
    KEYWORD_HEADER: str
    COMMENT_HEADER: str

    TESTCASE_NAME: str
    KEYWORD_NAME: str

    DOCUMENTATION: str
    SUITE_SETUP: str
    SUITE_TEARDOWN: str
    METADATA: str
    TEST_SETUP: str
    TEST_TEARDOWN: str
    TEST_TEMPLATE: str
    TEST_TIMEOUT: str
    FORCE_TAGS: str
    DEFAULT_TAGS: str
    LIBRARY: str
    RESOURCE: str
    VARIABLES: str
    SETUP: str
    TEARDOWN: str
    TEMPLATE: str
    TIMEOUT: str
    TAGS: str
    ARGUMENTS: str
    RETURN: str
    RETURN_SETTING: str

    NAME: str
    VARIABLE: str
    ARGUMENT: str
    ASSIGN: str
    KEYWORD: str
    WITH_NAME: str
    FOR: str
    FOR_SEPARATOR: str
    END: str
    IF: str
    INLINE_IF: str
    ELSE_IF: str
    ELSE: str
    TRY: str
    EXCEPT: str
    FINALLY: str
    AS: str
    WHILE: str
    RETURN_STATEMENT: str
    CONTINUE: str
    BREAK: str

    SEPARATOR: str
    COMMENT: str
    CONTINUATION: str
    EOL: str
    EOS: str

    ERROR: str
    FATAL_ERROR: str

    NON_DATA_TOKENS: frozenset
    SETTING_TOKENS: frozenset
    HEADER_TOKENS: frozenset
    ALLOW_VARIABLES: frozenset

    type: str
    value: str
    lineno: int
    col_offset: int
    error: str
    def __init__(
        self,
        type: str = None,
        value: str = None,
        lineno: int = -1,
        col_offset: int = -1,
        error: str = None,
    ):
        pass
    @property
    def end_col_offset(self) -> int:
        pass
    def set_error(self, error, fatal=False):
        pass
    def tokenize_variables(self):
        """Tokenizes possible variables in token value.

        Yields the token itself if the token does not allow variables (see
        :attr:`Token.ALLOW_VARIABLES`) or its value does not contain
        variables. Otherwise yields variable tokens as well as tokens
        before, after, or between variables so that they have the same
        type as the original token.
        """
        pass

class SuiteVisitor:
    def visit_suite(self, suite):
        """Implements traversing through suites.

        Can be overridden to allow modifying the passed in ``suite`` without
        calling :meth:`start_suite` or :meth:`end_suite` nor visiting child
        suites, tests or setup and teardown at all.
        """
    def start_suite(self, suite):
        """Called when a suite starts. Default implementation does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_suite(self, suite):
        """Called when a suite ends. Default implementation does nothing."""
    def visit_test(self, test):
        """Implements traversing through tests.

        Can be overridden to allow modifying the passed in ``test`` without calling
        :meth:`start_test` or :meth:`end_test` nor visiting the body of the test.
        """
    def start_test(self, test):
        """Called when a test starts. Default implementation does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_test(self, test):
        """Called when a test ends. Default implementation does nothing."""
    def visit_keyword(self, kw):
        """Implements traversing through keywords.

        Can be overridden to allow modifying the passed in ``kw`` without
        calling :meth:`start_keyword` or :meth:`end_keyword` nor visiting
        the body of the keyword
        """
    def start_keyword(self, keyword):
        """Called when a keyword starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_keyword(self, keyword):
        """Called when a keyword ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_for(self, for_):
        """Implements traversing through FOR loops.

        Can be overridden to allow modifying the passed in ``for_`` without
        calling :meth:`start_for` or :meth:`end_for` nor visiting body.
        """
    def start_for(self, for_):
        """Called when a FOR loop starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_for(self, for_):
        """Called when a FOR loop ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_for_iteration(self, iteration):
        """Implements traversing through single FOR loop iteration.

        This is only used with the result side model because on the running side
        there are no iterations.

        Can be overridden to allow modifying the passed in ``iteration`` without
        calling :meth:`start_for_iteration` or :meth:`end_for_iteration` nor visiting
        body.
        """
    def start_for_iteration(self, iteration):
        """Called when a FOR loop iteration starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_for_iteration(self, iteration):
        """Called when a FOR loop iteration ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_if(self, if_):
        """Implements traversing through IF/ELSE structures.

        Notice that ``if_`` does not have any data directly. Actual IF/ELSE branches
        are in its ``body`` and visited using :meth:`visit_if_branch`.

        Can be overridden to allow modifying the passed in ``if_`` without
        calling :meth:`start_if` or :meth:`end_if` nor visiting branches.
        """
    def start_if(self, if_):
        """Called when an IF/ELSE structure starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_if(self, if_):
        """Called when an IF/ELSE structure ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_if_branch(self, branch):
        """Implements traversing through single IF/ELSE branch.

        Can be overridden to allow modifying the passed in ``branch`` without
        calling :meth:`start_if_branch` or :meth:`end_if_branch` nor visiting body.
        """
    def start_if_branch(self, branch):
        """Called when an IF/ELSE branch starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_if_branch(self, branch):
        """Called when an IF/ELSE branch ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_try(self, try_):
        """Implements traversing through TRY/EXCEPT structures.

        This method is used with the TRY/EXCEPT root element. Actual TRY, EXCEPT, ELSE
        and FINALLY branches are visited separately using :meth:`visit_try_branch`.
        """
    def start_try(self, try_):
        """Called when a TRY/EXCEPT structure starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_try(self, try_):
        """Called when a TRY/EXCEPT structure ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_try_branch(self, branch):
        """Visits individual TRY, EXCEPT, ELSE and FINALLY branches."""
    def start_try_branch(self, branch):
        """Called when TRY, EXCEPT, ELSE or FINALLY branches start.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_try_branch(self, branch):
        """Called when TRY, EXCEPT, ELSE and FINALLY branches end.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_while(self, while_):
        """Implements traversing through WHILE loops.

        Can be overridden to allow modifying the passed in ``while_`` without
        calling :meth:`start_while` or :meth:`end_while` nor visiting body.
        """
    def start_while(self, while_):
        """Called when a WHILE loop starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_while(self, while_):
        """Called when a WHILE loop ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_while_iteration(self, iteration):
        """Implements traversing through single WHILE loop iteration.

        This is only used with the result side model because on the running side
        there are no iterations.

        Can be overridden to allow modifying the passed in ``iteration`` without
        calling :meth:`start_while_iteration` or :meth:`end_while_iteration` nor visiting
        body.
        """
    def start_while_iteration(self, iteration):
        """Called when a WHILE loop iteration starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_while_iteration(self, iteration):
        """Called when a WHILE loop iteration ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_return(self, return_):
        """Visits a RETURN elements."""
    def start_return(self, return_):
        """Called when a RETURN element starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_return(self, return_):
        """Called when a RETURN element ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_continue(self, continue_):
        """Visits CONTINUE elements."""
    def start_continue(self, continue_):
        """Called when a CONTINUE element starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_continue(self, continue_):
        """Called when a CONTINUE element ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_break(self, break_):
        """Visits BREAK elements."""
    def start_break(self, break_):
        """Called when a BREAK element starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_break(self, break_):
        """Called when a BREAK element ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def visit_message(self, msg):
        """Implements visiting messages.

        Can be overridden to allow modifying the passed in ``msg`` without
        calling :meth:`start_message` or :meth:`end_message`.
        """
    def start_message(self, msg):
        """Called when a message starts.

        By default, calls :meth:`start_body_item` which, by default, does nothing.

        Can return explicit ``False`` to stop visiting.
        """
    def end_message(self, msg):
        """Called when a message ends.

        By default, calls :meth:`end_body_item` which, by default, does nothing.
        """
    def start_body_item(self, item):
        """Called, by default, when keywords, messages or control structures start.

        More specific :meth:`start_keyword`, :meth:`start_message`, `:meth:`start_for`,
        etc. can be implemented to visit only keywords, messages or specific control
        structures.

        Can return explicit ``False`` to stop visiting. Default implementation does
        nothing.
        """
        pass
    def end_body_item(self, item):
        """Called, by default, when keywords, messages or control structures end.

        More specific :meth:`end_keyword`, :meth:`end_message`, `:meth:`end_for`,
        etc. can be implemented to visit only keywords, messages or specific control
        structures.

        Default implementation does nothing.
        """
        pass

def get_model(source, data_only=False, curdir=None, lang=None):
    pass
