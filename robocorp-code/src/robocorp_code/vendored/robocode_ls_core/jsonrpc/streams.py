# Original work Copyright 2018 Palantir Technologies, Inc. (MIT)
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Robocorp Technologies Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import threading
from robocorp_ls_core.robotframework_log import get_logger

try:
    import ujson as json
except Exception:  # pylint: disable=broad-except
    import json

log = get_logger(__name__)


class JsonRpcStreamReader(object):

    def __init__(self, rfile):
        self._rfile = rfile

    def close(self):
        self._rfile.close()

    def listen(self, message_consumer):
        """Blocking call to listen for messages on the rfile.

        Args:
            message_consumer (fn): function that is passed each message as it is read off the socket.
        """
        try:
            while not self._rfile.closed:
                try:
                    request_str = self._read_message()
                    log.debug("Read: %s", request_str)
                except ValueError:
                    if self._rfile.closed:
                        return
                    else:
                        log.exception("Failed to read from rfile")

                if request_str is None:
                    break

                try:
                    message_consumer(json.loads(request_str.decode("utf-8")))
                except ValueError:
                    log.exception("Failed to parse JSON message %s", request_str)
                    continue
        finally:
            log.debug("Exited JsonRpcStreamReader.")

    def _read_message(self):
        """Reads the contents of a message.

        Returns:
            body of message if parsable else None
        """

        content_length = None
        line = "<ignore>"

        # Blindly consume all header lines (until \r\n) except for the content-len.
        while line and line.strip():
            line = self._rfile.readline()
            if not line:
                return None
            if content_length is None:
                content_length = self._content_length(line)

        if not content_length:
            raise AssertionError("Error in protocol: did not find 'Content-Length:'.")

        # Grab the body
        buf = b""
        while True:
            data = self._rfile.read(content_length - len(buf))
            if not buf and len(data) == content_length:
                # Common case
                return data
            buf += data
            if len(buf) == content_length:
                return buf
            if len(buf) > content_length:
                raise AssertionError(
                    "Expected to read message up to len == %s (already read: %s). Found:\n%s"
                    % (content_length, len(buf), buf.decode("utf-8", "replace"))
                )
            # len(buf) < content_length (just keep on going).

    @staticmethod
    def _content_length(line):
        """Extract the content length from an input line."""
        if line.startswith(b"Content-Length: "):
            _, value = line.split(b"Content-Length: ")
            value = value.strip()
            try:
                return int(value)
            except ValueError:
                raise ValueError("Invalid Content-Length header: {}".format(value))

        return None


class JsonRpcStreamWriter(object):

    def __init__(self, wfile, **json_dumps_args):
        assert wfile is not None
        self._wfile = wfile
        self._wfile_lock = threading.Lock()
        self._json_dumps_args = json_dumps_args

    def close(self):
        log.debug("Will close writer")
        with self._wfile_lock:
            self._wfile.close()

    def write(self, message):
        with self._wfile_lock:
            if self._wfile.closed:
                log.debug("Unable to write %s (file already closed).", (message,))
                return False
            try:
                log.debug("Writing: %s", message)
                body = json.dumps(message, **self._json_dumps_args)

                # Ensure we get the byte length, not the character length
                content_length = (
                    len(body) if isinstance(body, bytes) else len(body.encode("utf-8"))
                )

                response = (
                    "Content-Length: {}\r\n"
                    "Content-Type: application/vscode-jsonrpc; charset=utf8\r\n\r\n"
                    "{}".format(content_length, body)
                )

                self._wfile.write(response.encode("utf-8"))
                self._wfile.flush()
                return True
            except Exception:  # pylint: disable=broad-except
                log.exception("Failed to write message to output file %s", message)
                return False
