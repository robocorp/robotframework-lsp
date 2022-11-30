import datetime
import json
from typing import Optional, Any
import sys

__version__ = "0.0.2"
version_info = [int(x) for x in __version__.split(".")]


_convert = {
    "gb": lambda s: s * 1e9,
    "g": lambda s: s * 1e9,
    "mb": lambda s: s * 1e6,
    "m": lambda s: s * 1e6,
    "kb": lambda s: s * 1000,
    "k": lambda s: s * 1000,
    "b": lambda s: s,
    "": lambda s: s,
}


def _convert_to_bytes(s):
    initial = s
    num = []
    while s and (s[0].isdigit() or s[0] == "."):
        num.append(s[0])
        s = s[1:]
    num = float("".join(num))
    unit = s.strip()
    conv = _convert.get(unit.lower())
    if conv is None:
        raise ValueError(f"Cannot get in bytes: {initial}")

    return conv(num)


class RFStream:

    # V3 would be nicer but it doesn't support keywords...
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, *args, **kwargs):
        from robot_out_stream._impl import _RobotOutputImpl, _Config

        # Note: expected to be used just when used in-memory.
        config = _Config(kwargs.get("__uuid__"))

        check_args = ["--dir=", "--max-file-size=", "--max-files=", "--log="]
        for arg in args:
            for check_arg in check_args:
                if arg.startswith(check_arg):
                    kwargs[check_arg[:-1]] = arg[len(check_arg) :]

        config.output_dir = kwargs.get("--dir", "./out_rfstream").replace(
            "<COLON>", ":"
        )
        if config.output_dir == "None":
            config.output_dir = None

        config.log_html = kwargs.get("--log")
        if config.log_html:
            config.log_html = config.log_html.replace("<COLON>", ":")

        max_file_size_arg = kwargs.get("--max-file-size", "1MB")
        config.max_file_size_in_bytes = _convert_to_bytes(max_file_size_arg)
        config.max_files = int(kwargs.get("--max-files", "5"))

        if config.max_file_size_in_bytes < 1000:
            raise ValueError(
                f"Cannot generate logs where the max file size in bytes is less that 1000 bytes."
                f" Found: {config.max_file_size_in_bytes}."
                f" Arg: {max_file_size_arg}."
            )

        # Attributes expected to be used just when used in-memory.
        config.write = kwargs.get("__write__")
        config.initial_time = kwargs.get("__initial_time__")
        config.additional_info = kwargs.get("__additional_info__")

        self._robot_output_impl = _RobotOutputImpl(config)

    @property
    def robot_output_impl(self):
        return self._robot_output_impl

    @property
    def initial_time(self) -> datetime.datetime:
        return self._robot_output_impl.initial_time

    def _get_time_delta(self, attributes) -> float:
        # i.e.: in general the time delta will not be there
        # it's only there for the case when we're reading
        # from the output.xml.
        time_delta = attributes.get("timedelta")
        if time_delta is not None:
            return time_delta
        return self._robot_output_impl.get_time_delta()

    def start_suite(self, name, attributes):
        # {
        #     "id": "s1",
        #     "longname": "Robot1",
        #     "doc": "",
        #     "metadata": {},
        #     "starttime": "20221003 14:20:02.195",
        #     "tests": ["First task", "Second task"],
        #     "suites": [],
        #     "totaltests": 2,
        #     "source": "C:\\Users\\...\\robot1.robot",
        # }
        return self._robot_output_impl.start_suite(
            name,
            attributes["id"],
            attributes["source"],
            self._get_time_delta(attributes),
        )

    def end_suite(self, name, attributes):
        # {
        #     "id": "s1",
        #     "longname": "Robot1",
        #     "doc": "",
        #     "metadata": {},
        #     "starttime": "20221004 09:38:40.271",
        #     "endtime": "20221004 09:38:40.323",
        #     "elapsedtime": 52,
        #     "status": "FAIL",
        #     "message": "",
        #     "tests": ["First task", "Second task"],
        #     "suites": [],
        #     "totaltests": 2,
        #     "source": "C:\\Users\\fabio\\AppData\\Local\\Temp\\pytest-of-fabio\\pytest-184\\test_robot_out_stream0\\test_robot_out_stream\\robot1.robot",
        #     "statistics": "2 tasks, 1 passed, 1 failed",
        # }
        return self._robot_output_impl.end_suite(
            attributes["status"], self._get_time_delta(attributes)
        )

    def start_test(self, name, attributes):
        # {
        #     "id": "s1-t1",
        #     "longname": "Robot1.First task",
        #     "doc": "",
        #     "tags": [],
        #     "lineno": 11,
        #     "source": "C:\\Users\\fabio\\...\\robot1.robot",
        #     "starttime": "20221003 14:20:02.231",
        #     "template": "",
        #     "originalname": "First task",
        # }
        return self._robot_output_impl.start_test(
            name,
            attributes["id"],
            attributes.get(
                "lineno"
            ),  # The source is already given by the suite (no need to repeat)
            self._get_time_delta(attributes),
            attributes.get("tags"),
        )

    def send_tag(self, tag: str):
        return self._robot_output_impl.send_tag(tag)

    def send_info(self, info: str):
        return self._robot_output_impl.send_info(info)

    def send_start_time_delta(self, time_delta_in_seconds: float):
        return self._robot_output_impl.send_start_time_delta(time_delta_in_seconds)

    def end_test(self, name, attributes):
        # {
        #     "id": "s1-t2",
        #     "longname": "Robot1.Second task",
        #     "doc": "",
        #     "tags": [],
        #     "lineno": 15,
        #     "source": "C:\\Users\\fabio\\AppData\\Local\\Temp\\pytest-of-fabio\\pytest-187\\test_robot_out_stream0\\test_robot_out_stream\\robot1.robot",
        #     "starttime": "20221004 16:23:10.403",
        #     "endtime": "20221004 16:23:10.412",
        #     "elapsedtime": 9,
        #     "status": "FAIL",
        #     "message": "Failed execution for some reason...",
        #     "template": "",
        #     "originalname": "Second task",
        # }
        return self._robot_output_impl.end_test(
            attributes["status"],
            attributes["message"],
            self._get_time_delta(attributes),
        )

    class _Sentinel:
        pass

    def start_keyword(self, name, attributes):

        # {
        #     "doc": "Does absolutely nothing.",
        #     "assign": [],
        #     "tags": [],
        #     "lineno": 7,
        #     "source": "C:\\Users\\fabio\\AppData\\Local\\Temp\\pytest-of-fabio\\pytest-170\\test_robot_out_stream0\\test_robot_out_stream\\robot1.robot",
        #     "type": "KEYWORD",
        #     "status": "NOT SET",
        #     "starttime": "20221003 16:20:21.234",
        #     "kwname": "No Operation",
        #     "libname": "BuiltIn",
        #     "args": [],
        # }
        source: Optional[str] = attributes.get("source", self._Sentinel)
        lineno: Optional[int] = attributes.get("lineno", self._Sentinel)
        if source is self._Sentinel or lineno is self._Sentinel:
            # I.e.: it was not passed at all (if it was passed and None,
            # keep it as None: xml conversion use-case).
            source = None
            lineno = -1

            # HACK for RF 3: try to get the location (since it's not available).
            f: Optional[Any]
            f = sys._getframe()
            while f is not None:
                if f.f_code.co_name == "run_step":
                    step = f.f_locals.get("step")
                    if step is not None:
                        try:
                            source = step.source
                            lineno = step.lineno
                        except AttributeError:
                            pass
                    break  # Break when run_step is found anyways.

                f = f.f_back

        return self._robot_output_impl.start_keyword(
            attributes["kwname"],
            attributes.get("libname"),
            attributes.get("type"),
            attributes.get("doc"),
            source,
            lineno,
            self._get_time_delta(attributes),
            attributes.get("args"),
            attributes.get("assign"),
        )

    def end_keyword(self, name, attributes):
        # {
        #     "doc": "Does absolutely nothing.",
        #     "assign": [],
        #     "tags": [],
        #     "lineno": 7,
        #     "source": "C:\\Users\\fabio\\AppData\\Local\\Temp\\pytest-of-fabio\\pytest-191\\test_robot_out_stream0\\test_robot_out_stream\\robot1.robot",
        #     "type": "KEYWORD",
        #     "status": "PASS",
        #     "starttime": "20221004 16:27:46.959",
        #     "endtime": "20221004 16:27:46.959",
        #     "elapsedtime": 0,
        #     "kwname": "No Operation",
        #     "libname": "BuiltIn",
        #     "args": [],
        # }
        return self._robot_output_impl.end_keyword(
            attributes["status"], self._get_time_delta(attributes)
        )

    def log_message(self, message, skip_error=True):
        # {
        #     "timestamp": "20221026 10:00:31.591",
        #     "message": "${dct} = {'a': '1', 'b': '1'}",
        #     "level": "INFO",
        #     "html": "no",
        # }
        level = message["level"]
        if level not in ("ERROR", "FAIL", "WARN", "INFO"):
            # Exclude TRACE/DEBUG/HTML for now (we could make that configurable...)
            return

        if skip_error and level in ("ERROR",):
            # We do this because in RF all the calls to 'log_message'
            # also generate a call to 'message', so, we want to skip
            # one of those (but note that the other way around isn't true
            # and some errors such as import errors are only reported
            # in 'message' and not 'log_message').
            return

        html = message.get("html")
        return self._robot_output_impl.log_message(
            level, message["message"], self._get_time_delta(message), html
        )

    def message(self, message):
        if message["level"] in ("FAIL", "ERROR"):
            return self.log_message(message, skip_error=False)

    def close(self):
        self.robot_output_impl.close()


def iter_decoded_log_format(stream):
    from ._decoder import iter_decoded_log_format

    return iter_decoded_log_format(stream)
