from pathlib import Path
from typing import Dict, Iterator, List, Sequence
import json
import itertools
import string
import datetime
from typing import Optional, Callable
import os
import traceback
from contextlib import contextmanager


_valid_chars = tuple(string.ascii_letters + string.digits)


def _gen_id(level: int = 1) -> Iterator[str]:
    iter_in = tuple(_valid_chars for _ in range(level))
    for entry in itertools.product(*iter_in):
        yield "".join(entry)

    # Recursively generate ids...
    yield from _gen_id(level + 1)


class _Config:
    # Loaded from constructor args
    output_dir: Optional[str]
    port: int
    max_file_size_in_bytes: int
    max_files: int

    # Loaded from constructor kwargs (to be used
    # only when used as an API).
    write: Optional[Callable[[str], None]] = None
    initial_time: Optional[datetime.datetime] = None
    additional_info: Optional[Sequence[str]] = None

    def __init__(self):
        self.output_dir = "./out_"
        self.port = -1


class _RotateHandler:
    def __init__(self, max_file_size_in_bytes: int, max_files: int):
        if max_files <= 0:
            raise ValueError(f"max_files must be > 0. Found: {max_files}")

        self._max_file_size_in_bytes = max_file_size_in_bytes
        self._total_bytes = 0

        self._found_files: List[Path] = []
        self._max_files = max_files

    def rotate_after(self, in_bytes: bytes):
        self._total_bytes += len(in_bytes)
        if self._total_bytes >= self._max_file_size_in_bytes:
            self._total_bytes = 0
            return True
        return False

    def register_file(self, filepath: Path):
        self._found_files.append(filepath)

        while len(self._found_files) > self._max_files:
            p: Path = self._found_files.pop(0)
            try:
                os.remove(p)
            except:
                traceback.print_exc()


class _StackHandler:
    def __init__(self):
        self._queue = []
        self._push_record = None
        self.recording_writes = False

    @contextmanager
    def push_record(self):
        assert self._push_record is None
        self.recording_writes = True
        self._push_record = []
        try:
            yield
        finally:
            self._queue.append(self._push_record)
            self._push_record = None
            self.recording_writes = False

    def record_msg(self, msg):
        self._push_record.append(msg)

    def pop(self):
        self._queue.pop(-1)

    def __iter__(self):
        for msg_or_list_msg in self._queue:
            if isinstance(msg_or_list_msg, (list, tuple)):
                yield from iter(msg_or_list_msg)

            else:
                yield msg_or_list_msg


class _RobotOutputImpl:
    def __init__(self, config: _Config):
        self._written_initial = False

        # Base memory for all streams (rotated or not)
        self._base_memo: Dict[str, str] = {}

        # Memory just for the current stream (if a name is not
        # here it has to be added because the output was rotated).
        self._current_memo: Dict[str, str] = {}

        self._config = config

        if config.output_dir is None:
            self._output_dir = None
        else:
            self._output_dir = Path(config.output_dir)
            self._output_dir.mkdir(exist_ok=True)
        self._write = config.write

        self._port = config.port

        self._move_old_runs()

        self._current_entry = -1
        self._current_file: Optional[Path] = None
        self._stream = None

        if config.initial_time is None:
            self._initial_time = datetime.datetime.now()
        else:
            self._initial_time = config.initial_time

        self._stack_handler = _StackHandler()

        self._rotate_handler = _RotateHandler(
            config.max_file_size_in_bytes, config.max_files
        )
        self._id_generator = _gen_id()

        if self._output_dir is not None:
            self._rotate_output()
        else:
            self._write_on_start_or_after_rotate()

    @property
    def current_file(self) -> Optional[Path]:
        return self._current_file

    @property
    def initial_time(self) -> datetime.datetime:
        return self._initial_time

    def _rotate_output(self):
        if self._output_dir is not None:
            self._current_memo = {}

            self._current_entry += 1
            if self._current_entry:
                self._current_file = (
                    self._output_dir / f"output_{self._current_entry}.rfstream"
                )
            else:
                self._current_file = self._output_dir / f"output.rfstream"

            if self._stream is not None:
                self._stream.close()
                self._stream = None

            self._rotate_handler.register_file(self._current_file)

            self._stream = self._current_file.open("wb")
            self._write_on_start_or_after_rotate()

    def _write_on_start_or_after_rotate(self):
        import sys

        if self._current_file is not None:
            print("Writing logs to", self._current_file.absolute())

        self._write_json("V ", 1)
        self._write_with_separator(
            "T ", (self._initial_time.isoformat(timespec="milliseconds"),)
        )
        if self._config.additional_info:
            for info in self._config.additional_info:
                self._write_json("I ", info)
        else:
            self._write_json("I ", f"sys.platform={sys.platform}")
            self._write_json("I ", f"python={sys.version}")
            import robot

            robot_version = robot.get_version()
            self._write_json("I ", f"robot={robot_version}")

        for msg_in_stack in self._stack_handler:
            self._do_write(msg_in_stack)

    def _do_write(self, s: str) -> None:
        if self._stack_handler.recording_writes:
            self._stack_handler.record_msg(s)

        if self._write is not None:
            self._write(s)

        in_bytes = s.encode("utf-8", errors="replace")
        if self._stream is not None:
            self._stream.write(in_bytes)
            self._stream.flush()
        if self._rotate_handler.rotate_after(in_bytes):
            self._rotate_output()

    def _write_json(self, msg_type, args):
        args_as_str = json.dumps(args)
        s = f"{msg_type}{args_as_str}\n"
        self._do_write(s)
        return s

    def _write_with_separator(self, msg_type, args):
        args_as_str = "|".join(args)
        s = f"{msg_type}{args_as_str}\n"
        self._do_write(s)
        return s

    def get_time_delta(self) -> float:
        delta = datetime.datetime.now() - self._initial_time
        return round(delta.total_seconds(), 3)

    def _move_old_runs(self):
        pass
        # TODO: Handle old runs (move to old runs).
        # for entry in self._output_dir.iterdir():
        #     print(entry)

    def _gen_id(self) -> str:
        while True:
            gen = next(self._id_generator)
            if gen not in self._base_memo:
                return gen

    def _obtain_id(self, s: str) -> str:
        curr_id = self._current_memo.get(s)
        if curr_id is not None:
            if self._stack_handler.recording_writes:
                self._stack_handler.record_msg(f"M {curr_id}:{json.dumps(s)}\n")
            return curr_id

        curr_id = self._base_memo.get(s)
        if curr_id is not None:
            self._write_json(f"M {curr_id}:", s)
            self._current_memo[s] = curr_id
            return curr_id

        new_id = self._gen_id()
        self._write_json(f"M {new_id}:", s)
        self._base_memo[s] = new_id
        self._current_memo[s] = new_id
        return new_id

    def _number(self, v):
        return str(v)

    def start_suite(self, name, suite_id, suite_source, time_delta):
        oid = self._obtain_id
        with self._stack_handler.push_record():
            self._write_with_separator(
                "SS ",
                [
                    oid(name),
                    oid(suite_id),
                    oid(suite_source),
                    self._number(time_delta),
                ],
            )

    def end_suite(self, status, time_delta):
        oid = self._obtain_id
        self._write_with_separator(
            "ES ",
            [
                oid(status),
                self._number(time_delta),
            ],
        )
        self._stack_handler.pop()

    def start_test(self, name, test_id, test_line, time_delta, tags):
        oid = self._obtain_id
        with self._stack_handler.push_record():
            self._write_with_separator(
                "ST ",
                [
                    oid(name),
                    oid(test_id),
                    self._number(test_line),
                    self._number(time_delta),
                ],
            )

            if tags:
                for tag in tags:
                    self.send_tag(tag)

    def send_tag(self, tag: str):
        oid = self._obtain_id
        self._write_with_separator(
            "TG ",
            [
                oid(tag),
            ],
        )

    def send_info(self, info: str):
        self._write_json("I ", info)

    def send_start_time_delta(self, time_delta_in_seconds: float):
        self._write_with_separator("S ", (self._number(time_delta_in_seconds),))

    def end_test(self, status, message, time_delta):
        oid = self._obtain_id
        self._write_with_separator(
            "ET ",
            [
                oid(status),
                oid(message),
                self._number(time_delta),
            ],
        )
        self._stack_handler.pop()

    def start_keyword(
        self,
        name,
        libname,
        keyword_type,
        doc,
        source,
        lineno,
        start_time_delta,
        args,
        assigns,
    ):
        keyword_type = keyword_type.upper()
        oid = self._obtain_id
        with self._stack_handler.push_record():
            self._write_with_separator(
                "SK ",
                [
                    oid(name),
                    oid(libname),
                    oid(keyword_type),
                    oid(doc),
                    oid(source),
                    self._number(lineno),
                    self._number(start_time_delta),
                ],
            )

            if assigns:
                for assign in assigns:
                    self._write_with_separator(
                        "AS ",
                        [
                            oid(assign),
                        ],
                    )
            if args:
                for arg in args:
                    self._write_with_separator(
                        "KA ",
                        [
                            oid(arg),
                        ],
                    )

    def end_keyword(self, status, time_delta):
        oid = self._obtain_id
        self._write_with_separator(
            "EK ",
            [
                oid(status),
                self._number(time_delta),
            ],
        )
        self._stack_handler.pop()

    def log_message(self, level, message, time_delta):
        oid = self._obtain_id
        self._write_with_separator(
            "L ",
            [
                # ERROR = E
                # FAIL = F
                # INFO = I
                # WARN = W
                level[0].upper(),
                oid(message),
                self._number(time_delta),
            ],
        )
