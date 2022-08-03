# Original work Copyright Fabio Zadrozny (EPL 1.0)
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

"""
Contains the main loops for our threads (reader_thread and writer_thread, which should
be initialized as the target of threading.Thread).

The reader_thread will read a message and ask a callable to deal with it and the
writer_thread just keeps on sending any message posted to the queue it receives.
"""

from functools import partial
import itertools
from robocorp_ls_core.robotframework_log import get_logger, get_log_level
import json
from typing import Optional, Dict


log = get_logger(__name__)

# Note: sentinel. Signals that the writer thread should stop processing.
STOP_WRITER_THREAD = "STOP_WRITER_THREAD"

# Note: sentinel. Sent by reader thread when stopped.
READER_THREAD_STOPPED = "READER_THREAD_STOPPED"


def read(stream, debug_prefix=b"read") -> Optional[Dict]:
    """
    Reads one message from the stream and returns the related dict (or None if EOF was reached).

    :param stream:
        The stream we should be reading from.

    :return dict|NoneType:
        The dict which represents a message or None if the stream was closed.
    """
    headers = {}
    while True:
        # Interpret the http protocol headers
        line = stream.readline()  # The trailing \r\n should be there.

        if get_log_level() > 1:
            log.debug(
                (
                    debug_prefix
                    + b": >>%s<<\n"
                    % (line.replace(b"\r", b"\\r").replace(b"\n", b"\\n"))
                ).decode("utf-8", "replace")
            )

        if not line:  # EOF
            return None
        line = line.strip().decode("ascii")
        if not line:  # Read just a new line without any contents
            break
        try:
            name, value = line.split(": ", 1)
        except ValueError:
            raise RuntimeError("Invalid header line: {}.".format(line))
        headers[name.strip()] = value.strip()

    if not headers:
        raise RuntimeError("Got message without headers.")

    content_length = int(headers["Content-Length"])

    # Get the actual json
    body = _read_len(stream, content_length)
    if get_log_level() > 1:
        log.debug((debug_prefix + b": %s" % (body,)).decode("utf-8", "replace"))

    try:
        return json.loads(body.decode("utf-8"))
    except:
        raise RuntimeError(f"Error reading: {body!r}")


def _read_len(stream, content_length) -> bytes:
    buf = b""
    if not content_length:
        return buf

    # Grab the body
    while True:
        data = stream.read(content_length - len(buf))
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


def reader_thread(
    stream,
    process_command,
    write_queue,
    debug_prefix=b"read",
    update_ids_from_dap=False,
):
    from robocorp_ls_core.debug_adapter_core.dap import dap_base_schema

    from robocorp_ls_core.debug_adapter_core.dap import (
        dap_schema,  # @UnusedImport -- register classes
    )
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Response

    try:
        while True:
            data = read(stream, debug_prefix)
            if data is None:
                break
            try:

                # A response with success == False doesn't need to be translated
                # as the original response (to avoid the validation).
                if not data.get("success", True) and data.get("type") == "response":
                    protocol_message = dap_base_schema.from_dict(
                        data, update_ids_from_dap=update_ids_from_dap, cls=Response
                    )
                else:
                    protocol_message = dap_base_schema.from_dict(
                        data, update_ids_from_dap=update_ids_from_dap
                    )
                process_command(protocol_message)
            except Exception as e:
                log.exception("Error processing message.")
                seq = data.get("seq")
                if seq:
                    error_msg = {
                        "type": "response",
                        "request_seq": seq,
                        "success": False,
                        "command": data.get("command", "<unknown"),
                        "message": "Error processing message: %s" % (e,),
                    }
                    write_queue.put(error_msg)
    except ConnectionError:
        if get_log_level() > 2:
            log.exception("ConnectionError (ignored).")
    except:
        log.exception("Error reading message.")
    finally:
        process_command(READER_THREAD_STOPPED)


def writer_thread_no_auto_seq(
    stream, queue, debug_prefix="write", update_ids_to_dap=False
):
    """
    Same as writer_thread but does not set the message 'seq' automatically
    (meant to be used when responses, which need the seq id set need to be handled).
    """
    try:
        while True:
            to_write = queue.get()
            if to_write is STOP_WRITER_THREAD:
                log.debug("STOP_WRITER_THREAD")
                stream.close()
                break

            if isinstance(to_write, dict):
                assert "seq" in to_write
                try:
                    to_write = json.dumps(to_write)
                except:
                    log.exception("Error serializing %s to json.", to_write)
                    continue

            else:
                to_json = getattr(to_write, "to_json", None)
                if to_json is not None:
                    # Some protocol message
                    assert to_write.seq >= 0
                    try:
                        to_write = to_json(update_ids_to_dap=update_ids_to_dap)
                    except:
                        log.exception("Error serializing %s to json.", to_write)
                        continue

            if get_log_level() > 1:
                log.debug(debug_prefix + ": %s\n", to_write)

            if to_write.__class__ == bytes:
                as_bytes = to_write
            else:
                as_bytes = to_write.encode("utf-8")

            stream.write(
                ("Content-Length: %s\r\n\r\n" % (len(as_bytes))).encode("ascii")
            )
            stream.write(as_bytes)
            stream.flush()
    except:
        log.exception("Error writing message.")
    finally:
        log.debug("Exit reader thread.")


def writer_thread(stream, queue, debug_prefix="write", update_ids_to_dap=False):
    """
    Same as writer_thread_no_auto_seq but sets the message 'seq' automatically.
    """
    _next_seq = partial(next, itertools.count())

    try:
        while True:
            to_write = queue.get()
            if to_write is STOP_WRITER_THREAD:
                log.debug("STOP_WRITER_THREAD")
                stream.close()
                break

            if isinstance(to_write, dict):
                to_write["seq"] = _next_seq()
                try:
                    to_write = json.dumps(to_write)
                except:
                    log.exception("Error serializing %s to json.", to_write)
                    continue

            else:
                to_json = getattr(to_write, "to_json", None)
                if to_json is not None:
                    # Some protocol message
                    to_write.seq = _next_seq()
                    try:
                        to_write = to_json(update_ids_to_dap=update_ids_to_dap)
                    except:
                        log.exception("Error serializing %s to json.", to_write)
                        continue

            if get_log_level() > 1:
                log.debug(debug_prefix + ": %s\n", to_write)

            if to_write.__class__ == bytes:
                as_bytes = to_write
            else:
                as_bytes = to_write.encode("utf-8")

            stream.write(
                ("Content-Length: %s\r\n\r\n" % (len(as_bytes))).encode("ascii")
            )
            stream.write(as_bytes)
            stream.flush()
    except ConnectionResetError:
        pass  # No need to log this
    except:
        log.exception("Error writing message.")
    finally:
        log.debug("Exit reader thread.")
