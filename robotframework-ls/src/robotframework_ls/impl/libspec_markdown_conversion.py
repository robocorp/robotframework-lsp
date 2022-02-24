from robotframework_ls.impl.text_utilities import get_digest_from_string
import os
from typing import Optional
from robotframework_ls.impl.protocols import ILibraryDoc
from robocorp_ls_core.robotframework_log import get_logger
import threading
import robotframework_ls
import robocorp_ls_core
import weakref
from robocorp_ls_core.basic import normalize_filename
import sys


log = get_logger(__name__)


def _get_mtime_from_stream(stream) -> Optional[float]:
    lst = []
    while True:
        c = stream.read(1)
        if c == "\n":
            break
        lst.append(c)
    line = "".join(lst).strip()

    if not line.startswith("mtime:"):
        log.info(
            "Expected %s contents to start with 'mtime:<saved_mtime>'\\n. Found: %s",
            target_json,
            line,
        )
        return None

    try:
        return float(line.split(":")[1])
    except:
        log.info(
            "Unable to load from json: %s because mtime line (%s) is not what we expected.",
            target_json,
            line,
        )
        return None


def load_markdown_json_version(
    libspec_manager, spec_filename, mtime: float
) -> Optional[ILibraryDoc]:
    from robotframework_ls.impl import robot_specbuilder

    target_json = _get_markdown_json_version_filename(libspec_manager, spec_filename)

    stream = None
    try:
        try:
            stream = open(target_json, "r", encoding="utf-8")
        except:
            log.debug("Unable to load from json: %s (file does not exist)", target_json)
        else:
            try:
                loaded_mtime = _get_mtime_from_stream(stream)

                if str(loaded_mtime) != str(mtime):
                    log.debug(
                        "Unable to load from json: %s because mtime no longer matches.",
                        target_json,
                    )
                    return None

                # Note: let the external world think it was built with the libspec
                # (so, the stream is from the json and the spec filename is from .libspec).
                json_builder = robot_specbuilder.JsonDocBuilder()
                return json_builder.build_from_stream(spec_filename, stream)
            except:
                log.exception("Error loading libdoc from json: %s", target_json)
                return None

    finally:
        if stream is not None:
            stream.close()

    return None


def _convert_to_markdown_if_needed(spec_filename, target_json) -> None:
    import tempfile
    import shutil

    try:
        with open(target_json, "r", encoding="utf-8") as existing_stream:
            current_mtime = _get_mtime_from_stream(existing_stream)
    except:
        current_mtime = None

    from robotframework_ls.impl import robot_specbuilder

    # If it raises because it's not there, that's ok!
    mtime = os.path.getmtime(spec_filename)

    if str(mtime) == str(current_mtime):
        # No need to convert, it still matches.
        return

    builder = robot_specbuilder.SpecDocBuilder()
    libdoc = builder.build(spec_filename)
    if libdoc.doc_format == "markdown":
        # i.e.: it's already in markdown.
        return

    libdoc.convert_docs_to_markdown()

    try:
        os.makedirs(os.path.dirname(target_json), exist_ok=True)
    except:
        pass

    with tempfile.NamedTemporaryFile(
        mode="w+", dir=os.path.dirname(target_json), delete=False, encoding="utf-8"
    ) as tempf:
        import json

        tempf.write(f"mtime:{mtime}\n")

        json.dump(libdoc.to_dictionary(), tempf)

    shutil.copy(tempf.name, target_json)
    os.remove(tempf.name)


class _ConversionThread(threading.Thread):

    DISPOSE = "DISPOSE"

    def __init__(self):
        import queue

        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = queue.Queue()

    def run(self):
        from robocorp_ls_core.subprocess_wrapper import subprocess

        while True:
            entry = self.queue.get()
            if entry == self.DISPOSE:
                return

            spec_filename, target_json = entry
            env = os.environ.copy()

            # Make sure we're in the pythonpath.
            env["PYTHONPATH"] = os.pathsep.join(
                [
                    os.path.dirname(os.path.dirname(robotframework_ls.__file__)),
                    os.path.dirname(os.path.dirname(robocorp_ls_core.__file__)),
                ]
            )

            try:
                subprocess.check_output(
                    [sys.executable, __file__, spec_filename, target_json],
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    env=env,
                )
            except subprocess.CalledProcessError as e:
                log.exception(
                    "Error converting libspec to markdown: %s.\nReturn code: %s\nOutput:\n%s",
                    spec_filename,
                    e.returncode,
                    e.output,
                )


def _get_markdown_json_version_filename(libspec_manager, spec_filename: str) -> str:
    spec_filename = normalize_filename(spec_filename)
    digest = get_digest_from_string(spec_filename)

    target_json = os.path.join(
        libspec_manager.cache_libspec_dir,
        f"{digest}_{os.path.basename(spec_filename)}.json",
    )
    return target_json


class LibspecMarkdownConversion:
    def __init__(self, libspec_manager):
        self._conversion_thread = _ConversionThread()
        self._started = False
        self._weak_libspec_manager = weakref.ref(libspec_manager)

    def get_markdown_json_version_filename(self, spec_filename: str) -> str:
        libspec_manager = self._weak_libspec_manager()
        assert libspec_manager is not None
        return _get_markdown_json_version_filename(libspec_manager, spec_filename)

    def schedule_conversion_to_markdown(self, spec_filename: str) -> Optional[str]:
        if not self._started:
            self._conversion_thread.start()
            self._started = True

        libspec_manager = self._weak_libspec_manager()
        if libspec_manager is None:
            self.dispose()
            return None

        target_json = self.get_markdown_json_version_filename(spec_filename)

        self._conversion_thread.queue.put((spec_filename, target_json))
        return target_json

    def dispose(self):
        self._conversion_thread.queue.put(_ConversionThread.DISPOSE)


if __name__ == "__main__":
    args = sys.argv[1:]

    try:
        spec_filename = args[0]
        target_json = args[1]
    except:
        sys.stderr.write(
            f"Expected 2 arguments (spec_filename, target_json). Received: {args}"
        )
        sys.stderr.flush()
        sys.exit(1)

    _convert_to_markdown_if_needed(spec_filename, target_json)
