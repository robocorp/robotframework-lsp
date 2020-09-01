import itertools
from functools import partial
import threading
from robocorp_ls_core.basic import implements
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.protocols import (
    ILanguageServerClientBase,
    Sentinel,
    COMMUNICATION_DROPPED,
)
from typing import Any, Union, Optional

log = get_logger(__name__)


class _MessageMatcher(object):
    def __init__(self):
        self.event = threading.Event()
        self.msg = None

    def notify(self, msg):
        # msg can be None if the communication was finished in the meanwhile.
        self.msg = msg
        self.event.set()


class _IdMessageMatcher(_MessageMatcher):
    def __init__(self, message_id):
        _MessageMatcher.__init__(self)

        self.message_id = message_id

    def __str__(self):
        return "IdMatcher(%s)" % (self.message_id,)

    __repr__ = __str__


class _PatternMessageMatcher(_MessageMatcher):
    def __init__(self, message_pattern):
        self.message_pattern = message_pattern
        _MessageMatcher.__init__(self)

    def matches(self, msg):
        for key, val in self.message_pattern.items():
            if msg.get(key) != val:
                return False
        return True

    def __str__(self):
        return "PatternMatcher(%s)" % (self.message_pattern,)

    __repr__ = __str__


class _ReaderThread(threading.Thread):
    def __init__(self, reader):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.reader = reader
        self._lock = threading.Lock()
        self._finished = False

        # Message matchers.
        self._id_message_matchers = {}  # msg id-> matcher
        self._pattern_message_matchers = {}  # id(matcher) -> matcher

    def run(self):
        try:
            self.reader.listen(self._on_message)
        finally:
            with self._lock:
                self._finished = True
                id_message_matchers = self._id_message_matchers
                self._id_message_matchers = {}

                pattern_message_matchers = self._pattern_message_matchers
                self._pattern_message_matchers = {}

            for message_matcher in id_message_matchers.values():
                message_matcher.notify(None)

            for message_matcher in pattern_message_matchers.values():
                message_matcher.notify(None)

    def _on_message(self, msg):
        from robocorp_ls_core.options import Setup

        notify_matchers = []
        log.debug("Will handle read message: %s" % (msg,))
        with self._lock:
            for message_matcher in self._pattern_message_matchers.values():
                if message_matcher.matches(msg):
                    notify_matchers.append(message_matcher)

            for message_matcher in notify_matchers:
                del self._pattern_message_matchers[id(message_matcher)]

            if "id" in msg:
                message_matcher = self._id_message_matchers.pop(msg["id"], None)
                if message_matcher is not None:
                    notify_matchers.append(message_matcher)

            if Setup.options.DEBUG_MESSAGE_MATCHERS:
                log.debug(
                    "Notify matchers: %s\nRemaining id matchers: %s\nRemaining pattern matchers: %s"
                    % (
                        notify_matchers,
                        self._id_message_matchers,
                        self._pattern_message_matchers,
                    )
                )

        for message_matcher in notify_matchers:
            message_matcher.notify(msg)

    def obtain_pattern_message_matcher(self, message_pattern):
        """
        :param message_pattern:
            Obtains a matcher which will be notified when the given message pattern is
            returned.
            
        :return:
            None if it's already finished or the message matcher otherwise.
        """
        with self._lock:
            if self._finished:
                return None
            message_matcher = _PatternMessageMatcher(message_pattern)
            self._pattern_message_matchers[id(message_matcher)] = message_matcher
            return message_matcher

    def obtain_id_message_matcher(self, message_id):
        """
        :param message_id:
            Obtains a matcher which will be notified when the given message id is
            returned.
            
        :return:
            None if it's already finished or the message matcher otherwise.
        """
        with self._lock:
            if self._finished:
                return None
            message_matcher = _IdMessageMatcher(message_id)
            self._id_message_matchers[message_id] = message_matcher
            return message_matcher


class LanguageServerClientBase(object):
    """
    A base implementation for talking with a process that implements the language
    server.
    """

    DEFAULT_TIMEOUT: Optional[
        int
    ] = None  # The default if not redefined is not having a timeout.

    def __init__(self, writer, reader):
        """
        
        :param JsonRpcStreamWriter writer:
        :param JsonRpcStreamReader reader:
        """
        self.writer = writer
        self.reader = reader

        t = _ReaderThread(reader)
        self._reader_thread = t
        t.start()
        self.require_exit_messages = True
        self.next_id = partial(next, itertools.count())

    @implements(ILanguageServerClientBase.request_async)
    def request_async(self, contents: dict):
        message_id = contents["id"]
        message_matcher = self._reader_thread.obtain_id_message_matcher(message_id)
        if message_matcher is None:
            return None

        if not self.write(contents):
            return None

        return message_matcher

    @implements(ILanguageServerClientBase.request)
    def request(
        self,
        contents,
        timeout: Union[int, Sentinel, None] = Sentinel.USE_DEFAULT_TIMEOUT,
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
        if timeout is Sentinel.USE_DEFAULT_TIMEOUT:
            timeout = self.DEFAULT_TIMEOUT

        message_id = contents["id"]
        message_matcher = self._reader_thread.obtain_id_message_matcher(message_id)
        if message_matcher is None:
            if timeout:
                raise TimeoutError(
                    "Request timed-out (%s) - no message matcher: %s"
                    % (timeout, contents)
                )
            return default

        if not self.write(contents):
            if timeout:
                raise TimeoutError(
                    "Request timed-out (%s) - no write: %s" % (timeout, contents)
                )
            return default

        if not message_matcher.event.wait(timeout=timeout):
            raise TimeoutError("Request timed-out (%s): %s" % (timeout, contents))

        return message_matcher.msg

    @implements(ILanguageServerClientBase.obtain_pattern_message_matcher)
    def obtain_pattern_message_matcher(self, message_pattern):
        return self._reader_thread.obtain_pattern_message_matcher(message_pattern)

    @implements(ILanguageServerClientBase.obtain_id_message_matcher)
    def obtain_id_message_matcher(self, message_id):
        return self._reader_thread.obtain_id_message_matcher(message_id)

    @implements(ILanguageServerClientBase.write)
    def write(self, contents):
        return self.writer.write(contents)

    @implements(ILanguageServerClientBase.shutdown)
    def shutdown(self):
        self.write({"jsonrpc": "2.0", "id": self.next_id(), "method": "shutdown"})

    @implements(ILanguageServerClientBase.exit)
    def exit(self):
        self.write({"jsonrpc": "2.0", "id": self.next_id(), "method": "exit"})
