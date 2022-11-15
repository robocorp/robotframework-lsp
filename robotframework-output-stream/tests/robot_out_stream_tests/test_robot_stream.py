from contextlib import contextmanager
import functools
import sys
import io
from pathlib import Path
from typing import Optional
import pytest
from robot_out_stream.robot_version import get_robot_major_version

# Flags to debug during development (should be == False on repository).
show_summary = False
show_contents = False
show_out_as_json_str = False
build_contents_locally = False


@contextmanager
def after(obj, method_name, callback):
    original_method = getattr(obj, method_name)

    @functools.wraps(original_method)
    def new_method(*args, **kwargs):
        ret = original_method(*args, **kwargs)
        callback(*args, **kwargs)
        return ret

    setattr(obj, method_name, new_method)
    try:
        yield
    finally:
        setattr(obj, method_name, original_method)


class _GeneratedInfo:
    def __init__(self, robot_out_stream, xml_output: Path, outdir: Path):
        from robot_out_stream import RFStream

        self.robot_out_stream: RFStream = robot_out_stream
        self.outdir: Path = outdir
        self.xml_output: Path = xml_output


def run_with_listener(
    datadir,
    outdir: Optional[Path] = None,
    max_file_size="500kb",
    max_files=5,
    robot_file: Optional[Path] = None,
) -> _GeneratedInfo:
    import robot
    from robot_out_stream import RFStream

    if outdir is None:
        outdir = datadir / "out"
        if build_contents_locally:
            outdir = Path(".") / "out_test"

    created = []

    def on_created(robot_out_stream, *args, **kwargs):
        created.append(robot_out_stream)

    with after(RFStream, "__init__", on_created):
        outdir_to_listener = str(outdir).replace(":", "<COLON>")
        if robot_file is None:
            robot_file = datadir / "robot1.robot"
        xml_output = outdir / "output.xml"
        report_output = outdir / "report.html"
        log_output = outdir / "log.html"
        robot.run_cli(
            [
                "-l",
                str(log_output),
                "-r",
                str(report_output),
                "-o",
                str(xml_output),
                "--listener",
                f"robot_out_stream.RFStream:--dir={outdir_to_listener}:--max-file-size={max_file_size}:--max-files={max_files}",
                str(robot_file),
            ],
            exit=False,
        )

    assert len(created) == 1

    if show_summary:
        print(f"output.xml size: {xml_output.stat().st_size/8} bytes")
    return _GeneratedInfo(created[0], xml_output, outdir)


@pytest.mark.skipif(
    get_robot_major_version() < 4, reason="Not available on older versions of robot."
)
def test_rotate_logs(datadir):
    generated_info = run_with_listener(
        datadir, robot_file=datadir / "robot2.robot", max_file_size="50kb", max_files=2
    )
    files = tuple(generated_info.outdir.glob("*.rfstream"))
    assert len(files) == 2, f"Found: {files}"


def test_robot_out_stream(datadir):
    from robot_out_stream import iter_decoded_log_format
    from io import StringIO

    generated_info = run_with_listener(datadir)
    robot_out_stream = generated_info.robot_out_stream
    xml_output = generated_info.xml_output

    impl = robot_out_stream.robot_output_impl
    assert impl.current_file.exists()
    contents = impl.current_file.read_text("utf-8")
    if show_contents:
        print("Contents of: ", impl.current_file)
        print("-----")
        print(contents)
        print("-----")

    if show_out_as_json_str:
        import json

        print(repr(json.dumps(contents)))

    if show_summary:
        print("-----")
        print(f"Size: {len(contents)/8} bytes")
        print("-----")

    decoded_len = 0
    for line in iter_decoded_log_format(StringIO(contents)):
        if show_contents:
            print(line)
        decoded_len += len(line)

    if show_summary:
        print(f"Decoded size: {decoded_len/8} bytes")

    from robot_out_stream.xml_to_rfstream import (
        convert_xml_to_rfstream,
    )

    txt = xml_output.read_text("utf-8")

    source = io.StringIO()
    source.write(txt)
    source.seek(0)

    converted = generated_info.outdir / "converted_xml.rfstream"
    with open(converted, "w") as stream:

        def write(s):
            if show_contents:
                sys.stdout.write(s)
            stream.write(s)

        convert_xml_to_rfstream(source, write=write)

    # contents = converted.read_text("utf-8")
    # for line in iter_decoded_log_format(StringIO(contents)):
    #     print(line)


def iter_with_test_replacements(filepath):
    from io import StringIO
    from robot_out_stream import iter_decoded_log_format

    contents = filepath.read_text("utf-8")

    for msg in iter_decoded_log_format(StringIO(contents)):
        if "time_delta_in_seconds" in msg:
            msg["time_delta_in_seconds"] = 0
        if "initial_time" in msg:
            msg["initial_time"] = "2022-10-31T10:00:00.000"
        if "suite_source" in msg:
            msg["suite_source"] = "<source>"
        if "source" in msg:
            msg["source"] = "<source>"
        if "doc" in msg:
            msg["doc"] = "<doc>"
        if "info" in msg:
            continue
        yield msg


def check(datadir, data_regression, name):
    generated_info = run_with_listener(datadir, robot_file=datadir / name)
    robot_out_stream = generated_info.robot_out_stream
    impl = robot_out_stream.robot_output_impl
    found = list(iter_with_test_replacements(impl.current_file))
    # for l in found:
    #     print(l)
    data_regression.check(found)


def test_robot_assign(datadir, data_regression):
    check(datadir, data_regression, "robot6.robot")


def test_robot_tags(datadir, data_regression):
    check(datadir, data_regression, "robot7.robot")


@pytest.mark.skipif(
    get_robot_major_version() < 5, reason="Not available on older versions of robot."
)
def test_robot_while(datadir, data_regression):
    check(datadir, data_regression, "robot5.robot")


@pytest.mark.skipif(
    get_robot_major_version() < 4, reason="Not available on older versions of robot."
)
def test_robot_if(datadir, data_regression):
    check(datadir, data_regression, "robot8.robot")


@pytest.mark.skipif(
    get_robot_major_version() < 5, reason="Not available on older versions of robot."
)
def test_robot_try_except(datadir, data_regression):
    check(datadir, data_regression, "robot9.robot")


@pytest.mark.skipif(
    get_robot_major_version() < 5, reason="Not available on older versions of robot."
)
def test_robot_return(datadir, data_regression):
    check(datadir, data_regression, "robot10.robot")
