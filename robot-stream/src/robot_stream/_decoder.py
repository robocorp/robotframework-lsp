import datetime
import json


def version_decode(decoder, message: str) -> str:
    return f"VERSION: {message}"


def simple_decode(decoder, message: str) -> str:
    return f"INFO: {json.loads(message)}"


def decode_time(decoder, time):
    decoder.initial_time = datetime.datetime.fromisoformat(time)
    return f"INITIAL_TIME: {time}"


def decode_memo(decoder, message):
    memo_id, memo_value = message.split(":", 1)
    memo_value = json.loads(memo_value)
    decoder.memo[memo_id] = memo_value
    return None


red = "\u001b[31m"
green = "\u001b[32m"
yellow = "\u001b[33m"
blue = "\u001b[34m"
magenta = "\u001b[35m"
cyan = "\u001b[36m"
white = "\u001b[37m"
reset = "\u001b[0m"


def _color_status(status):
    if status == "PASS":
        return f"{green}{status}{reset}"
    elif status == "NOT RUN":
        return f"{cyan}{status}{reset}"
    else:
        return f"{red}{status}{reset}"


def _color_name(status):
    return f"{yellow}{status}{reset}"


def start_suite(decoder, message):
    ident = decoder.ident
    decoder.level += 1
    name_id, suite_id_id, suite_source_id, time_delta_in_seconds = message.split("|")
    name = _color_name(decoder.memo[name_id])
    suite_id = decoder.memo[suite_id_id]
    suite_source = decoder.memo[suite_source_id]
    return f"{ident}START SUITE: name: {name} - id: {suite_id} - source: {suite_source} - elapsed: {time_delta_in_seconds}s"


def end_suite(decoder, message):
    decoder.level -= 1
    ident = decoder.ident
    status_id, time_delta_in_seconds = message.split("|")
    status = _color_status(decoder.memo[status_id])
    return f"{ident}END SUITE: status: {status} - elapsed: {time_delta_in_seconds}s"


def start_task_or_test(decoder, message):
    ident = decoder.ident
    decoder.level += 1
    name_id, suite_id_id, line, time_delta = message.split("|")
    name = _color_name(decoder.memo[name_id])
    suite_id = decoder.memo[suite_id_id]
    return f"{ident}START TASK/TEST: name: {name} - id: {suite_id} - line: {line} - elapsed: {time_delta}s"


def end_task_or_test(decoder, message):
    decoder.level -= 1
    ident = decoder.ident
    status_id, message_id, time_delta_in_seconds = message.split("|")
    status = _color_status(decoder.memo[status_id])
    message = decoder.memo[message_id]
    return f"{ident}END TASK/TEST: status: {status} - message: {message} - elapsed: {time_delta_in_seconds}s"


def start_keyword(decoder, message):
    ident = decoder.ident
    decoder.level += 1
    (
        name_id,
        libname_id,
        type_id,
        doc_id,
        source_id,
        lineno,
        time_delta_in_seconds,
    ) = message.split("|")
    keyword_type = _color_name(decoder.memo[type_id])
    name = _color_name(decoder.memo[name_id])
    libname = decoder.memo[libname_id]
    doc = decoder.memo[doc_id]
    source = decoder.memo[source_id]
    return f"{ident}START {keyword_type}: name: {name} - libname: {libname} - doc: {doc} - elapsed: {time_delta_in_seconds}s"


def end_keyword(decoder, message):
    decoder.level -= 1
    ident = decoder.ident
    status_id, time_delta_in_seconds = message.split("|")
    status = _color_status(decoder.memo[status_id])

    return f"{ident}END: status: {status} - elapsed: {time_delta_in_seconds}s"


def decode_log(decoder, message):
    ident = decoder.ident
    level, message_id, time_delta_in_seconds = message.split("|")
    message = decoder.memo[message_id]

    return f"{ident}LOG: level: {level}: {message} - elapsed: {time_delta_in_seconds}s"


def keyword_argument(decoder, message):
    return f"{decoder.ident}KEYWORD ARGUMENT: {decoder.memo[message]}"


_MESSAGE_TYPE_INFO = {
    "V": version_decode,
    "I": simple_decode,
    "T": decode_time,
    "M": decode_memo,
    "L": decode_log,
    "SS": start_suite,
    "ES": end_suite,
    "ST": start_task_or_test,
    "ET": end_task_or_test,
    "SK": start_keyword,
    "EK": end_keyword,
    "KA": keyword_argument,
}


class Decoder:
    def __init__(self):
        self.memo = {}
        self.initial_time = None
        self.level = 0

    @property
    def ident(self):
        return "    " * self.level

    def decode_message_type(self, message_type, message):
        handler = _MESSAGE_TYPE_INFO[message_type]
        return handler(self, message)


def iter_decoded_log_format(stream):
    decoder = Decoder()
    for line in stream.readlines():
        line = line.strip()
        if line:
            message_type, message = line.split(" ", 1)
            decoded = decoder.decode_message_type(message_type, message)
            if decoded:
                yield decoded
