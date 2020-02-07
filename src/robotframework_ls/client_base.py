import logging
import itertools
from functools import partial
import threading

log = logging.getLogger(__name__)


class _MessageMatcher(object):
    def __init__(self):
        self.event = threading.Event()
        self.msg = None

    def notify(self, msg):
        self.msg = msg
        self.event.set()


class _ReaderThread(threading.Thread):
    def __init__(self, reader, queue):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.reader = reader
        self.queue = queue
        self._message_matchers = {}

    def run(self):
        self.reader.listen(self._put_into_queue)

    def _put_into_queue(self, msg):
        if "id" in msg:
            message_matcher = self._message_matchers.get(msg["id"])
            if message_matcher is not None:
                message_matcher.notify(msg)
        self.queue.put(msg)

    def obtain_message_matcher(self, message_id):
        message_matcher = self._message_matchers[message_id] = _MessageMatcher()
        return message_matcher


class LanguageServerClientBase(object):
    """
    A base implementation for talking with a process that implements the language
    server.
    """

    TIMEOUT = None

    def __init__(self, writer, reader):
        """
        
        :param JsonRpcStreamWriter writer:
        :param JsonRpcStreamReader reader:
        """
        try:
            from queue import Queue
        except:
            from Queue import Queue

        self.writer = writer
        self.reader = reader
        self._queue = Queue()

        t = _ReaderThread(reader, self._queue)
        self._reader_thread = t
        t.start()
        self.require_exit_messages = True
        self.next_id = partial(next, itertools.count())

    def request(self, contents, timeout=None):
        message_id = contents["id"]
        message_matcher = self._reader_thread.obtain_message_matcher(message_id)
        self.write(contents)
        if not message_matcher.event.wait(timeout=timeout):
            raise AssertionError("Request timed-out (%s): %s" % (timeout, contents,))

        return message_matcher.msg

    def write(self, contents):
        self.writer.write(contents)

    def next_message(self, block=True, timeout=None):
        if timeout is None:
            timeout = self.TIMEOUT
        return self._queue.get(block=block, timeout=self.TIMEOUT)

    def wait_for_message(self, match):
        found = False
        while not found:
            msg = self.next_message()
            for key, value in match.items():
                if msg.get(key) == value:
                    continue

                log.info("Message found:\n%s\nwhile waiting for\n%s" % (msg, match))
                break
            else:
                found = True
        return msg

    def shutdown(self):
        self.write(
            {"jsonrpc": "2.0", "id": self.next_id(), "method": "shutdown",}
        )

    def exit(self):
        self.write(
            {"jsonrpc": "2.0", "id": self.next_id(), "method": "exit",}
        )
