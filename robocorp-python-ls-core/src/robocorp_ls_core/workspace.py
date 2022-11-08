# Original work Copyright 2017 Palantir Technologies, Inc. (MIT)
# Original work Copyright 2020 Open Law Library. (Apache 2)
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
import io
import os
from typing import Optional, Dict, List, Iterable, Tuple, Set, Union, Any

from robocorp_ls_core import uris
from robocorp_ls_core.basic import implements
from robocorp_ls_core.protocols import (
    IWorkspace,
    IDocument,
    IDocumentSelection,
    IWorkspaceFolder,
    IConfig,
)
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.uris import uri_scheme, to_fs_path, normalize_drive, normalize_uri
import threading
from robocorp_ls_core.lsp import (
    TextDocumentItem,
    TextDocumentContentChangeEvent,
    RangeTypedDict,
    TextEditTypedDict,
    TextEdit,
)
import weakref
from collections import namedtuple
import time
from robocorp_ls_core.watchdog_wrapper import IFSObserver

log = get_logger(__name__)

_FileMTimeInfo = namedtuple("_FileMTimeInfo", "st_mtime, st_size")


def _text_edit_key(text_edit: Union[TextEditTypedDict, TextEdit]):
    start = text_edit["range"]["start"]
    return start["line"], start["character"]


class _DirInfo(object):
    def __init__(self, scan_path):
        self.scan_path = scan_path
        self.files_in_directory: Set[str] = set()


class _VirtualFSThread(threading.Thread):

    SLEEP_AMONG_SCANS = 0.5
    INNER_SLEEP = 0.1

    def __init__(self, virtual_fs):
        from robocorp_ls_core.watchdog_wrapper import IFSWatch
        from robocorp_ls_core import load_ignored_dirs
        from robocorp_ls_core.callbacks import Callback

        threading.Thread.__init__(self)
        self.daemon = True

        self._virtual_fs = weakref.ref(virtual_fs)
        self.root_folder_path = virtual_fs.root_folder_path

        self.accept_directory = load_ignored_dirs.create_accept_directory_callable()
        self.accept_file = lambda path_name: path_name.endswith(
            tuple(virtual_fs._extensions)
        )
        self._disposed = threading.Event()
        self.first_check_done = threading.Event()
        self._check_done_events = []
        self._last_sleep = None
        self._fs_watch: Optional[IFSWatch] = None
        self._dirs_changed = set()
        self._trigger_loop = threading.Event()
        self.on_file_changed = Callback()

    def _check_need_sleep(self):
        last_sleep = self._last_sleep
        if last_sleep is None:
            self._last_sleep = time.time()
            return
        if time.time() - last_sleep > 0.3:
            time.sleep(self.INNER_SLEEP)
            self._last_sleep = time.time()

    def _check_dir(self, dir_path: str, directories: Set[str], level=0, recursive=True):
        # This is the actual poll loop
        if level > 20:  # At most 20 levels deep...
            log.critical(
                "Directory tree more than 20 levels deep: %s. Bailing out.", dir_path
            )
            return

        self._last_sleep = time.time()
        if self._disposed.is_set():
            return

        dir_path = normalize_drive(dir_path)
        directories.add(dir_path)
        dir_info = _DirInfo(dir_path)
        try:
            assert not isinstance(dir_path, bytes)
            if self._disposed.is_set():
                return

            i = 0
            for entry in os.scandir(dir_path):
                i += 1

                if i % 100 == 0:
                    self._check_need_sleep()
                if entry.is_dir():
                    if recursive and self.accept_directory(entry.path):
                        self._check_dir(entry.path, directories, level + 1)

                elif self.accept_file(entry.path):
                    dir_info.files_in_directory.add(normalize_drive(entry.path))

            virtual_fs = self._virtual_fs()
            if virtual_fs is None:
                return
            virtual_fs._dir_to_info[dir_path] = dir_info
        except OSError:
            pass  # Directory was removed in the meanwhile.

    def run(self):
        from robocorp_ls_core.watchdog_wrapper import PathInfo

        virtual_fs: _VirtualFS = self._virtual_fs()
        fs_observer: IFSObserver = virtual_fs._fs_observer

        # Setup tracking for changes
        self._fs_watch = fs_observer.notify_on_any_change(
            [PathInfo(self.root_folder_path, recursive=True)],
            on_change=self._on_change,
            extensions=virtual_fs._extensions,
        )
        check_done_events = self._check_done_events
        self._check_done_events = []

        # Do initial scan
        self._check_dir(self.root_folder_path, set())

        # Notify of initial scan
        self.first_check_done.set()
        self._notify_check_done_events(check_done_events)

        while not self._disposed.is_set():
            self._trigger_loop.wait(self.SLEEP_AMONG_SCANS)
            if self._disposed.is_set():
                return

            check_done_events = self._check_done_events
            self._check_done_events = []

            # Wait 100 more millis to catch up to further changes in the same loop.
            time.sleep(0.1)

            virtual_fs = self._virtual_fs()
            if virtual_fs is None:
                self.dispose()
                return

            # This would do a clean update, which'd be very cost intensive...
            # Instead, let's work only on the `_dirs_changed`.
            # directories = set()
            # current = list(virtual_fs._dir_to_info)
            # self._check_dir(self.root_folder_path, directories)
            #
            # for d in current:
            #     if d not in directories:
            #         virtual_fs._dir_to_info.pop(d, None)

            dirs_changed = self._dirs_changed
            self._dirs_changed = set()

            for dir_path in dirs_changed:
                dir_path = normalize_drive(dir_path)
                dir_info = _DirInfo(dir_path)
                try:
                    assert not isinstance(dir_path, bytes)
                    if self._disposed.is_set():
                        return

                    for entry in os.scandir(dir_path):
                        if not entry.is_dir() and self.accept_file(entry.path):
                            dir_info.files_in_directory.add(entry.path)
                except OSError:
                    if not os.path.exists(dir_path):
                        # Directory was removed.
                        virtual_fs._dir_to_info.pop(dir_path, None)
                else:
                    virtual_fs._dir_to_info[dir_path] = dir_info

            virtual_fs = None

            self._trigger_loop.clear()
            self._notify_check_done_events(check_done_events)

    def _on_change(self, src_path):
        changed_dir = os.path.dirname(src_path)
        self._dirs_changed.add(changed_dir)
        self._trigger_loop.set()
        self.on_file_changed(src_path)

    def dispose(self):
        fs_watch = self._fs_watch
        if fs_watch is not None:
            fs_watch.stop_tracking()
            self._fs_watch = None

        self._disposed.set()
        self._trigger_loop.set()

    def _notify_check_done_events(self, check_done_events):
        for event in check_done_events:
            event.set()

    def wait_for_check_done(self, timeout):
        event = threading.Event()
        self._check_done_events.append(event)
        if not event.wait(timeout):
            raise TimeoutError()


class _VirtualFS(object):
    def __init__(
        self, root_folder_path: str, extensions: Iterable[str], fs_observer: IFSObserver
    ):
        self.root_folder_path = normalize_drive(root_folder_path)

        self._dir_to_info: Dict[str, _DirInfo] = {}

        self._extensions = set(extensions)
        self._fs_observer = fs_observer

        # Do initial scan and then start tracking changes.
        self._virtual_fsthread = _VirtualFSThread(self)
        self._virtual_fsthread.start()
        self.on_file_changed = self._virtual_fsthread.on_file_changed

    def wait_for_check_done(self, timeout):
        self._virtual_fsthread.wait_for_check_done(timeout)

    def _iter_all_doc_uris(self, extensions: Tuple[str, ...]) -> Iterable[str]:
        """
        :param extensions:
            The extensions which are being searched (i.e.: ('.txt', '.py')).
        """
        assert self._extensions.issuperset(extensions)
        dir_infos = list(self._dir_to_info.values())
        for dir_info in dir_infos:
            for f in dir_info.files_in_directory:
                if f.endswith(extensions):
                    yield uris.from_fs_path(f)

    def dispose(self):
        self._virtual_fsthread.dispose()
        self._dir_to_info.clear()


class _WorkspaceFolderWithVirtualFS(object):
    """
    Walking a big tree may be time consuming, and very wasteful if users have
    things which the language server doesn't need (for instance, having a
    node_modules with thousands of unrelated files in the workspace).

    This class helps in keeping a cache just with the files we care about and
    invalidating them as needed.
    """

    def __init__(self, uri, name, track_file_extensions, fs_observer: IFSObserver):
        self.uri = uri
        self.name = name
        self.path = uris.to_fs_path(uri)

        self._vs: _VirtualFS = _VirtualFS(
            self.path, track_file_extensions, fs_observer=fs_observer
        )
        self.on_file_changed = self._vs.on_file_changed

    def _iter_all_doc_uris(self, extensions: Tuple[str, ...]) -> Iterable[str]:
        """
        :param extensions:
            The extensions which are being searched (i.e.: ('.txt', '.py')).
        """
        # Note: this function is meant to be thread-safe.

        vs = self._vs
        yield from vs._iter_all_doc_uris(extensions)

    def wait_for_check_done(self, timeout):
        self._vs.wait_for_check_done(timeout)

    def dispose(self):
        self._vs.dispose()

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IWorkspaceFolder = check_implements(self)


class Workspace(object):
    """
    Note: only a single thread can mutate the workspace, but multiple threads
    may read from it.
    """

    def __init__(
        self,
        root_uri: str,
        fs_observer: IFSObserver,
        workspace_folders: Optional[List[IWorkspaceFolder]] = None,
        track_file_extensions=(".robot", ".resource", ".py", ".yml", ".yaml"),
    ) -> None:
        from robocorp_ls_core.lsp import WorkspaceFolder
        from robocorp_ls_core.callbacks import Callback
        from robocorp_ls_core.cache import LRUCache

        self._main_thread = threading.current_thread()

        self._root_uri = root_uri
        self._root_uri_scheme = uri_scheme(self._root_uri)
        self._root_path = to_fs_path(self._root_uri)
        self._folders: Dict[str, _WorkspaceFolderWithVirtualFS] = {}
        self._track_file_extensions = track_file_extensions
        self._fs_observer = fs_observer

        # Contains the docs with files considered open.
        self._docs: Dict[str, IDocument] = {}

        # Contains the docs pointing to the filesystem.
        def _get_size(doc: IDocument):
            # In a simplistic way we say that each char in a document occupies
            # 8 bytes and then multiply this by 7.5 to account for the supposed
            # amount of memory used by the AST which is cached along in the document
            return 8 * len(doc.source) * 7.5

        one_gb_in_bytes = int(1e9)
        target_memory_in_bytes: int = one_gb_in_bytes  # Default value

        target_memory_in_bytes_str = os.environ.get(
            "RFLS_FILES_TARGET_MEMORY_IN_BYTES", None
        )
        if target_memory_in_bytes_str:
            try:
                target_memory_in_bytes = int(target_memory_in_bytes_str)
            except:
                log.critical(
                    "Expected RFLS_FILES_TARGET_MEMORY_IN_BYTES to evaluate to an int. Found: %s",
                    target_memory_in_bytes,
                )

        fifty_mb_in_bytes = int(5e7)
        if target_memory_in_bytes <= fifty_mb_in_bytes:
            target_memory_in_bytes = fifty_mb_in_bytes

        # Whenever we reach 1GB of used memory we clear up to use 700 MB.
        self._filesystem_docs: LRUCache[str, IDocument] = LRUCache(
            target_memory_in_bytes, get_size=_get_size
        )
        self._filesystem_docs_lock = threading.Lock()

        self.on_file_changed = Callback()

        if workspace_folders is not None:
            for folder in workspace_folders:
                self.add_folder(folder)

        if root_uri and root_uri not in self._folders:
            as_fs_path = uris.to_fs_path(root_uri)
            name = os.path.basename(as_fs_path)
            self.add_folder(WorkspaceFolder(root_uri, name))

    def on_changed_config(self, config: IConfig) -> None:
        pass

    def _check_in_mutate_thread(self):
        curr_thread = threading.current_thread()
        if self._main_thread is not curr_thread:
            raise AssertionError(
                f"Mutating the workspace can only be done at the thread: {self._main_thread}. Current thread: {curr_thread}"
            )

    def _create_document(
        self, doc_uri, source=None, version=None, force_load_source=False
    ):
        return Document(
            doc_uri,
            source=source,
            version=version,
            mutate_thread=self._main_thread,
            force_load_source=force_load_source,
        )

    def add_folder(self, folder: IWorkspaceFolder):
        """
        :param WorkspaceFolder folder:
        """
        self._check_in_mutate_thread()
        if folder.uri not in self._folders:
            folders = self._folders.copy()
            folder = _WorkspaceFolderWithVirtualFS(
                folder.uri,
                folder.name,
                track_file_extensions=self._track_file_extensions,
                fs_observer=self._fs_observer,
            )
            folder.on_file_changed.register(self.on_file_changed)
            folders[folder.uri] = folder
            self._folders = folders

    def remove_folder(self, folder_uri: str):
        self._check_in_mutate_thread()
        if folder_uri in self._folders:
            folders = self._folders.copy()
            folder = folders.pop(folder_uri)
            folder.on_file_changed.unregister(self.on_file_changed)
            folder.dispose()
            self._folders = folders

    @implements(IWorkspace.iter_documents)
    def iter_documents(self) -> Iterable[IDocument]:
        self._check_in_mutate_thread()  # i.e.: we don't really mutate here, but this is not thread safe.
        return self._docs.values()

    def get_open_docs_uris(self) -> List[str]:
        return list(d.uri for d in self._docs.values())

    @implements(IWorkspace.iter_folders)
    def iter_folders(self) -> Iterable[IWorkspaceFolder]:
        return (
            self._folders.values()
        )  # Ok, thread-safe (folders are always set as a whole)

    def wait_for_check_done(self, timeout):
        for folder in self.iter_folders():
            folder.wait_for_check_done(timeout)

    @implements(IWorkspace.get_folder_paths)
    def get_folder_paths(self) -> List[str]:
        folders = self._folders  # Ok, thread-safe (folders are always set as a whole)
        return [uris.to_fs_path(ws_folder.uri) for ws_folder in folders.values()]

    @implements(IWorkspace.get_document)
    def get_document(self, doc_uri: str, accept_from_file: bool) -> Optional[IDocument]:
        # Ok, thread-safe (does not mutate the _docs dict so the GIL keeps us
        # safe -- contents in the _filesystem_docs need a lock though).
        doc = self._docs.get(normalize_uri(doc_uri))
        if doc is not None:
            return doc

        if accept_from_file:
            with self._filesystem_docs_lock:
                doc = self._filesystem_docs.get(doc_uri)

                if doc is not None:
                    if not doc.is_source_in_sync():
                        self._filesystem_docs.pop(doc_uri, None)
                        doc = None

                if doc is None:
                    try:
                        doc = self._create_document(doc_uri, force_load_source=True)
                    except:
                        log.debug("Unable to load contents from: %s", doc_uri)
                        # Unable to load contents: file does not exist.
                        doc = None
                    else:
                        doc.immutable = True
                        self._filesystem_docs[doc_uri] = doc

        return doc

    def is_local(self):
        # Thread-safe (only accesses immutable data).
        return (
            self._root_uri_scheme == "" or self._root_uri_scheme == "file"
        ) and os.path.exists(self._root_path)

    @implements(IWorkspace.put_document)
    def put_document(self, text_document: TextDocumentItem) -> IDocument:
        self._check_in_mutate_thread()
        doc_uri = text_document.uri
        normalized_doc_uri = normalize_uri(doc_uri)
        doc = self._docs[normalized_doc_uri] = self._create_document(
            doc_uri, source=text_document.text, version=text_document.version
        )
        try:
            # In case the initial text wasn't passed, try to load it from source.
            # If it doesn't work, set the initial source as empty.
            # Note that we already checked the thread in this function, so, we
            # don't need to force it to be gotten in the constructor (which
            # could raise an exception).
            _source = doc.source
        except:
            doc.source = ""
        with self._filesystem_docs_lock:
            self._filesystem_docs.pop(normalized_doc_uri, None)
        return doc

    @implements(IWorkspace.remove_document)
    def remove_document(self, uri: str) -> None:
        self._check_in_mutate_thread()
        self._docs.pop(normalize_uri(uri), None)

    @property
    def root_path(self):
        # Thread-safe (only accesses immutable data).
        return self._root_path

    @property
    def root_uri(self) -> str:
        # Thread-safe (only accesses immutable data).
        return self._root_uri

    def update_document(
        self, text_doc: TextDocumentItem, change: TextDocumentContentChangeEvent
    ) -> IDocument:
        self._check_in_mutate_thread()
        doc_uri = text_doc["uri"]
        normalized_uri = normalize_uri(doc_uri)
        doc = self._docs[normalized_uri]

        # Note: don't mutate an existing doc, always create a new one based on it
        # (so, existing references won't have racing conditions).
        new_doc = self._create_document(doc_uri, doc.source, text_doc["version"])
        new_doc.apply_change(change)
        self._docs[normalized_uri] = new_doc
        return new_doc

    def iter_all_doc_uris_in_workspace(
        self, extensions: Tuple[str, ...]
    ) -> Iterable[str]:
        """
        :param extensions:
            The extensions which are being searched (i.e.: ('.txt', '.py')).
        """

        # Folders are set as a whole, so, this is thread safe.
        # This may be called in a thread.
        folders = self._folders.values()
        for folder in folders:
            yield from folder._iter_all_doc_uris(extensions)

    def dispose(self):
        self._check_in_mutate_thread()

        # Stop tracking folders and clear doc references.
        for folder_uri in list(self._folders.keys()):
            self.remove_folder(folder_uri)

        self._docs = {}
        with self._filesystem_docs_lock:
            self._filesystem_docs.clear()

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IWorkspace = check_implements(self)


class Document(object):
    """
    Note: the doc isn't inherently thread-safe, so, the workspace should create
    a new document instead of mutating the source.

    Everything else (apart from changing the source) should be thread-safe
    (even without locks -- sometimes we may end up calculating things more than
    once, but that should not corrupt internal structures).
    """

    def __init__(
        self,
        uri: str,
        source=None,
        version: Optional[str] = None,
        *,
        mutate_thread=None,
        force_load_source=False,
    ):
        # During construction, set the mutate thread to the current thread.
        self._main_thread = threading.current_thread()
        self.immutable = False

        self.uri = uri
        self.version = version
        self.path = uris.to_fs_path(uri)  # Note: may be None.

        self._source = source
        self.__line_start_offsets = None

        # Only set when the source is read from disk.
        self._source_mtime = -1

        if force_load_source:
            # Just accessing should be ok to load the source.
            _ = self.source

        if mutate_thread is not None:
            # After construction it may only be mutated by the mutate thread if
            # specified.
            self._main_thread = mutate_thread

    def _check_in_mutate_thread(self):
        curr_thread = threading.current_thread()
        if self._main_thread is not curr_thread:
            raise AssertionError(
                f"Mutating the document can only be done at the thread: {self._main_thread}. Current thread: {curr_thread}"
            )

    def __str__(self):
        return str(self.uri)

    def __len__(self):
        return len(self.source)

    def __bool__(self):
        return True

    __nonzero__ = __bool__

    def selection(self, line, col) -> IDocumentSelection:
        from robocorp_ls_core.document_selection import DocumentSelection

        return DocumentSelection(self, line, col)

    @property
    def _source(self) -> str:
        return self.__source

    @_source.setter
    def _source(self, source: str) -> None:
        # i.e.: when the source is set, reset the lines.
        self._check_in_mutate_thread()
        if self.immutable:
            raise RuntimeError(
                "This document is immutable, so, its source cannot be changed."
            )
        self.__source = source
        self._clear_caches()

    def _clear_caches(self):
        self._check_in_mutate_thread()
        self.__lines = None
        self.__line_start_offsets = None

    @property
    def _lines(self):
        lines = self.__lines
        if lines is None:
            lines = self.__lines = tuple(self.source.splitlines(True))
        return lines

    def get_internal_lines(self):
        return self._lines

    def iter_lines(self, keep_ends=True):
        lines = self._lines
        line = ""
        for line in lines:
            if keep_ends:
                yield line
            else:
                yield line.rstrip("\r\n")

        # If the last line ends with a new line, yield the final empty string.
        if line.endswith("\r") or line.endswith("\n"):
            yield ""

    def _compute_line_start_offsets(self):
        line_start_offset_to_info = self.__line_start_offsets
        if line_start_offset_to_info is None:

            line_start_offset_to_info = []
            offset = 0
            for line in self.iter_lines():
                line_start_offset_to_info.append(offset)
                offset += len(line)

        self.__line_start_offsets = line_start_offset_to_info
        return line_start_offset_to_info

    def offset_to_line_col(self, offset: int) -> Tuple[int, int]:
        if offset < 0:
            raise ValueError("Expected offset to be >0. Found: %s" % (offset,))

        import bisect

        line_start_offset_to_info = self._compute_line_start_offsets()
        i_line = bisect.bisect_left(line_start_offset_to_info, offset)
        if (
            i_line >= len(line_start_offset_to_info)
            or line_start_offset_to_info[i_line] > offset
        ):
            i_line -= 1
        line_start_offset = line_start_offset_to_info[i_line]
        return (i_line, offset - line_start_offset)

    def get_range(self, line: int, col: int, endline: int, endcol: int) -> str:
        if line >= self.get_line_count():
            return ""

        if line == endline:
            if endcol <= col:
                return ""

            line_contents = self.get_line(line)
            return line_contents[col:endcol]

        full_contents = []
        for i_line in range(line, min(endline + 1, self.get_line_count())):
            line_contents = self.get_line(i_line)
            if i_line == line:
                full_contents.append(self._lines[i_line][col:])
            elif i_line == endline:
                full_contents.append(self._lines[i_line][:endcol])
            else:
                full_contents.append(self._lines[i_line])
        return "".join(full_contents)

    def _load_source(self, mtime=None):
        self._check_in_mutate_thread()
        if mtime is None:
            mtime = os.path.getmtime(self.path)

        self._source_mtime = mtime
        with io.open(self.path, "r", encoding="utf-8") as f:
            self._source = f.read()

    @implements(IDocument.is_source_in_sync)
    def is_source_in_sync(self):
        try:
            mtime = os.path.getmtime(self.path)
            return self._source_mtime == mtime
        except Exception:
            log.info("Unable to get mtime for: %s", self.path)
            return False

    @property
    def source(self):
        if self._source is None:
            self._load_source()
        return self._source

    @source.setter
    def source(self, source):
        self._source = source

    @implements(IDocument.get_line)
    def get_line(self, line: int) -> str:
        try:
            return self._lines[line].rstrip("\r\n")
        except IndexError:
            return ""

    def get_last_line(self) -> str:
        try:
            last_line = self._lines[-1]
            if last_line.endswith("\r") or last_line.endswith("\n"):
                return ""
            return last_line
        except IndexError:
            return ""

    def get_last_line_col(self) -> Tuple[int, int]:
        lines = self._lines
        if not lines:
            return (0, 0)
        else:
            last_line = lines[-1]
            if last_line.endswith("\r") or last_line.endswith("\n"):
                return len(lines), 0
            return len(lines) - 1, len(last_line)

    def get_last_line_col_with_contents(self, contents: str) -> Tuple[int, int]:
        if not contents:
            raise ValueError("Contents not specified.")

        for i, line_contents in enumerate(self.iter_lines(keep_ends=False)):
            if contents in line_contents:
                return i, len(line_contents)
        raise RuntimeError(f"Unable to find line with contents: {contents}.")

    def get_line_count(self) -> int:
        lines = self._lines
        return len(lines)

    def apply_change(self, change: TextDocumentContentChangeEvent) -> None:
        """Apply a change to the document."""
        self._check_in_mutate_thread()
        text = change["text"]
        change_range: Optional[RangeTypedDict] = change.get("range")
        self._apply_change(change_range, text)

    def _apply_change(self, change_range: Optional[RangeTypedDict], text):
        self._check_in_mutate_thread()
        if not change_range:
            # The whole file has changed

            self._source = text
            return

        start_line = change_range["start"]["line"]
        start_col = change_range["start"]["character"]
        end_line = change_range["end"]["line"]
        end_col = change_range["end"]["character"]

        # Check for an edit occurring at the very end of the file
        if start_line == len(self._lines):

            self._source = self.source + text
            return

        new = io.StringIO()

        # Note: we could probably improve this sometime to work better with big documents
        # (but the link with the AST must be well thought out too).
        # References:
        # https://news.ycombinator.com/item?id=30415868
        # https://news.ycombinator.com/item?id=15381886
        # https://code.visualstudio.com/blogs/2018/03/23/text-buffer-reimplementation
        # https://blog.jetbrains.com/fleet/2022/02/fleet-below-deck-part-ii-breaking-down-the-editor/
        # https://raphlinus.github.io/xi/2020/06/27/xi-retrospective.html

        # Iterate over the existing document until we hit the edit range,
        # at which point we write the new text, then loop until we hit
        # the end of the range and continue writing.
        for i, line in enumerate(self._lines):
            if i < start_line:
                new.write(line)
                continue

            if i > end_line:
                new.write(line)
                continue

            if i == start_line:
                new.write(line[:start_col])
                new.write(text)

            if i == end_line:
                new.write(line[end_col:])

        self._source = new.getvalue()

    def apply_text_edits(
        self, text_edits: Union[List[TextEditTypedDict], List[TextEdit]]
    ):
        self._check_in_mutate_thread()
        sorted_text_edits = reversed(sorted(text_edits, key=_text_edit_key))
        text_edit: Any
        for text_edit in sorted_text_edits:
            self._apply_change(text_edit["range"], text_edit["newText"])

    def find_line_with_contents(self, contents: str) -> int:
        """
        :param contents:
            The contents to be found.

        :return:
            The 0-based index of the contents.
        """
        for i, line in enumerate(self.iter_lines()):
            if contents in line:
                return i
        else:
            raise AssertionError(f"Did not find >>{contents}<< in doc.")

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IDocument = check_implements(self)
