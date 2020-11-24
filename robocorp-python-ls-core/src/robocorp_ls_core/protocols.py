import sys
import threading
from typing import (
    Dict,
    Union,
    Any,
    Generic,
    Callable,
    Mapping,
    Optional,
    List,
    Type,
    Iterator,
)
from typing import TypeVar
import typing

from enum import Enum

# Hack so that we don't break the runtime on versions prior to Python 3.8.
if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass

    class TypedDict(object):
        def __init_subclass__(self, *args, **kwargs):
            pass


else:
    from typing import Protocol
    from typing import TypedDict


T = TypeVar("T")
Y = TypeVar("Y", covariant=True)


class Sentinel(Enum):
    SENTINEL = 0
    USE_DEFAULT_TIMEOUT = 1


def check_implements(x: T) -> T:
    """
    Helper to check if a class implements some protocol. 

    :important: It must be the last method in a class due to
                https://github.com/python/mypy/issues/9266

	Example:

    def __typecheckself__(self) -> None:
        _: IExpectedProtocol = check_implements(self)

    Mypy should complain if `self` is not implementing the IExpectedProtocol.
    """
    return x


class IFuture(Generic[Y], Protocol):
    def result(self, timeout: typing.Optional[int] = None) -> Y:
        """Return the result of the call that the future represents.

        Args:
            timeout: The number of seconds to wait for the result if the future
                isn't done. If None, then there is no limit on the wait time.

        Returns:
            The result of the call that the future represents.

        Raises:
            CancelledError: If the future was cancelled.
            TimeoutError: If the future didn't finish executing before the given
                timeout.
            Exception: If the call raised then that exception will be raised.
        """

    def add_done_callback(self, fn: Callable[["IFuture"], Any]):
        """Attaches a callable that will be called when the future finishes.

        Args:
            fn: A callable that will be called with this future as its only
                argument when the future completes or is cancelled. The callable
                will always be called by a thread in the same process in which
                it was added. If the future has already completed or been
                cancelled then the callable will be called immediately. These
                callables are called in the order that they were added.
        """


class IEndPoint(Protocol):
    def notify(self, method: str, params: Any = None):
        """Send a JSON RPC notification to the client.

         Args:
             method (str): The method name of the notification to send
             params (any): The payload of the notification
         """

    def request(self, method: str, params=None) -> IFuture:
        """Send a JSON RPC request to the client.

        Args:
            method (str): The method name of the message to send
            params (any): The payload of the message

        Returns:
            Future that will resolve once a response has been received
        """

    def consume(self, message: Dict):
        """Consume a JSON RPC message from the client.

        Args:
            message (dict): The JSON RPC message sent by the client
        """


class CommunicationDropped(object):
    pass


class IMessageMatcher(Generic[T], Protocol):

    event: threading.Event
    msg: T


class IIdMessageMatcher(IMessageMatcher, Protocol):

    message_id: str


COMMUNICATION_DROPPED = CommunicationDropped()


class IRequestCancellable(Protocol):
    def request_cancel(self, message_id) -> None:
        """
        Requests that some processing is cancelled.
        """


class ILanguageServerClientBase(IRequestCancellable, Protocol):
    def request_async(self, contents: Dict) -> Optional[IIdMessageMatcher]:
        """
        API which allows to wait for the message to complete.
        
        To use:
            message_matcher = client.request_async(contents)
            if message_matcher is not None:
                if message_matcher.event.wait(5):
                    ...
                    msg = message_matcher.msg
                else:
                    # Timed out
            
        :param contents:
            Something as:
            {"jsonrpc": "2.0", "id": msg_id, "method": method_name, "params": params}
            
        :return _MessageMatcher:
        """

    def request(
        self,
        contents,
        timeout: Union[int, Sentinel] = Sentinel.USE_DEFAULT_TIMEOUT,
        default: Any = COMMUNICATION_DROPPED,
    ):
        """
        :param contents:
        :param timeout:
        :return:
            The returned message if everything goes ok.
            `default` if the communication dropped in the meanwhile and timeout was None.
        
        :raises:
            TimeoutError if the timeout was given and no answer was given at the available time
            (including if the communication was dropped).
        """

    def obtain_pattern_message_matcher(
        self, message_pattern: Dict[str, str]
    ) -> IMessageMatcher:
        """
        Can be used as:
        
        message_matcher = language_server.obtain_pattern_message_matcher(
            {"method": "textDocument/publishDiagnostics"}
        )
        """

    def obtain_id_message_matcher(self, message_id) -> IMessageMatcher:
        pass

    def write(self, contents):
        pass

    def shutdown(self):
        pass

    def exit(self):
        pass


class IRobotFrameworkApiClient(ILanguageServerClientBase, Protocol):
    def initialize(
        self, msg_id=None, process_id=None, root_uri="", workspace_folders=()
    ):
        pass

    def get_version(self):
        pass

    def lint(self, doc_uri: str) -> list:
        pass

    def request_lint(self, doc_uri: str) -> Optional[IIdMessageMatcher]:
        pass

    def forward(self, method_name, params):
        pass

    def forward_async(self, method_name, params) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """

    def open(self, uri, version, source):
        pass

    def request_section_name_complete(
        self, doc_uri, line, col
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """

    def request_keyword_complete(
        self, doc_uri, line, col
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """

    def request_complete_all(self, doc_uri, line, col) -> Optional[IIdMessageMatcher]:
        """
        Completes: sectionName, keyword, variables
        :Note: async complete.
        """

    def request_find_definition(
        self, doc_uri, line, col
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """

    def request_source_format(
        self, text_document, options
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """

    def request_signature_help(
        self, doc_uri: str, line: int, col: int
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """

    def request_workspace_symbols(
        self, query: Optional[str] = None
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """


class ILanguageServerClient(ILanguageServerClientBase, Protocol):
    pid: Optional[int]

    DEFAULT_TIMEOUT: Optional[int] = None

    def settings(self, settings: Dict):
        """
        :param settings:
            Something as: 
            {"settings": {"robot": {"pythonpath": [case4_path]}}}
        """

    def initialize(
        self, root_path: str, msg_id=None, process_id=None, initialization_options=None
    ):
        pass

    def change_workspace_folders(
        self, added_folders: List[str], removed_folders: List[str]
    ) -> None:
        pass

    def open_doc(self, uri: str, version: int = 1, text: Optional[str] = None):
        """
        :param text:
            If None (default), the contents will be loaded from the disk.
        """

    def change_doc(self, uri: str, version: int, text: str):
        pass

    def get_completions(self, uri: str, line: int, col: int):
        """
        :param uri:
            The uri for the request.
        :param line:
            0-based line.
        :param col:
            0-based col.
        """

    def request_source_format(self, uri: str):
        """
        :param uri:
            The uri for the request.
        """

    def find_definitions(self, uri, line: int, col: int):
        """
        :param uri:
            The uri for the request.
        :param line:
            0-based line.
        :param col:
            0-based col.
        """

    def execute_command(self, command: str, arguments: list) -> Mapping[str, Any]:
        pass

    def execute_command_async(
        self, command: str, arguments: list
    ) -> Optional[IIdMessageMatcher]:
        pass

    def request_signature_help(self, uri: str, line: int, col: int):
        pass

    def request_workspace_symbols(self, query: Optional[str] = None):
        pass


class IConfig(Protocol):
    def get_setting(
        self, key: str, expected_type: Any, default=Sentinel.SENTINEL
    ) -> Any:
        """
        :param key:
            The setting to be gotten (i.e.: my.setting.to.get)
            
        :param expected_type:
            The type which we're expecting.
            
        :param default:
            If given, return this value instead of throwing a KeyError.
            
        :raises:
            KeyError if the setting could not be found and default was not provided.
        """

    def update(self, settings: dict) -> None:
        """Recursively merge the given settings into the current settings."""

    def get_full_settings(self) -> dict:
        pass

    def set_override_settings(self, override_settings: dict):
        pass


class ILog(Protocol):
    def critical(self, msg: str = "", *args: Any):
        pass

    def info(self, msg: str = "", *args: Any):
        pass

    def warn(self, msg: str = "", *args: Any):
        pass  # same as info

    def warning(self, msg: str = "", *args: Any):
        pass  # same as info

    def debug(self, msg: str = "", *args: Any):
        pass

    def exception(self, msg: str = "", *args: Any):
        pass

    def error(self, msg: str = "", *args: Any):
        pass  # same as exception


class IConfigProvider(Protocol):
    @property
    def config(self) -> IConfig:
        pass


class ILanguageServer(IConfigProvider):
    pass


class IDirCache(Protocol):
    """
    """

    def store(self, key: Any, value: Any) -> None:
        """
        Persists the given key and value.

        :param key:
            The key to be persisted. It's repr(key) is used to calculate
            the key filename on the disk. 
            
        :note that the values do a round-trip with json (so, caveats
        such as saving a tuple and loading a list apply).
        """

    def load(self, key: Any, expected_class: Type) -> Any:
        """
        Loads a previously persisted value.
        
        If it doesn't exist, there's some error loading or the expected 
        class doesn't match the loaded value a KeyError is thrown. 
        
        :note: users should check that the cache value is what's expected when it's
           gotten (as the data may become corrupted on disk or may change across
           versions).
        """

    def discard(self, key: Any) -> None:
        """
        Removes some key from the cache.
        """


class IDocumentSelection(Protocol):

    doc: "IDocument"
    line: int
    col: int

    @property
    def offset_at_position(self):
        """Return the byte-offset pointed at by the given position."""
        pass

    @property
    def current_line(self) -> str:
        pass

    @property
    def line_to_column(self):
        pass

    @property
    def word_at_column(self) -> str:
        pass

    @property
    def word_to_column(self) -> str:
        pass

    @property
    def word_from_column(self) -> str:
        pass


class IDocument(Protocol):
    uri: str
    version: Optional[str]
    path: str

    def selection(self, line: int, col: int) -> IDocumentSelection:
        pass

    @property
    def source(self) -> str:
        pass

    @source.setter
    def source(self, source: str) -> None:
        pass

    def get_line(self, line: int) -> str:
        pass

    def is_source_in_sync(self) -> bool:
        """
        If the document is backed up by a file, returns true if the sources are
        in sync.
        """


class IWorkspaceFolder(Protocol):
    uri: str
    name: str


class IWorkspace(Protocol):
    @property
    def root_path(self):
        pass

    @property
    def root_uri(self):
        pass

    def iter_documents(self) -> Iterator[IDocument]:
        """
        Note: the lock must be obtained when iterating documents.
        """

    def iter_folders(self) -> Iterator[IWorkspaceFolder]:
        """
        Note: the lock must be obtained when iterating folders.
        """

    def remove_document(self, uri: str) -> None:
        pass

    def put_document(
        self, text_document: "robocorp_ls_core.lsp.TextDocumentItem"  # type: ignore
    ) -> IDocument:
        pass

    def get_document(self, doc_uri: str, accept_from_file: bool) -> Optional[IDocument]:
        """
        Return a managed document if-present, otherwise, create one pointing at
        the disk if accept_from_file == True (if the file exists, and we're able to
        load it, otherwise, return None).
        """

    def get_folder_paths(self) -> List[str]:
        """
        Retuns the folders which are set as workspace folders.
        """


class ITimeoutHandle(Protocol):
    def exec_on_timeout(self):
        pass


class IMonitor(Protocol):
    def cancel(self) -> None:
        pass

    def check_cancelled(self) -> None:
        """
        raises JsonRpcRequestCancelled if cancelled.
        """
