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
from typing import Optional, Dict, List

import robocorp_ls_core  # noqa -- for typing.
from robocorp_ls_core import uris
from robocorp_ls_core.basic import implements
from robocorp_ls_core.protocols import IWorkspace, IDocument, IDocumentSelection
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.uris import uri_scheme, to_fs_path
import threading


log = get_logger(__name__)


class Workspace(object):
    """
    Note: only a single thread can mutate the workspace, but multiple threads
    may read from it.
    """

    def __init__(self, root_uri, workspace_folders=None) -> None:
        from robocorp_ls_core.lsp import WorkspaceFolder

        self._main_thread = threading.current_thread()

        self._root_uri = root_uri
        self._root_uri_scheme = uri_scheme(self._root_uri)
        self._root_path = to_fs_path(self._root_uri)
        self._folders: Dict[str, WorkspaceFolder] = {}

        # Contains the docs with files considered open.
        self._docs: Dict[str, IDocument] = {}

        # Contains the docs pointing to the filesystem.
        self._filesystem_docs: Dict[str, IDocument] = {}

        if workspace_folders is not None:
            for folder in workspace_folders:
                self.add_folder(folder)

        if root_uri and root_uri not in self._folders:
            as_fs_path = uris.to_fs_path(root_uri)
            name = os.path.basename(as_fs_path)
            self.add_folder(WorkspaceFolder(root_uri, name))

    def _check_in_mutate_thread(self):
        curr_thread = threading.current_thread()
        if self._main_thread is not curr_thread:
            raise AssertionError(
                f"Mutating the workspace can only be done at the thread: {self._main_thread}. Current thread: {curr_thread}"
            )

    def _create_document(self, doc_uri, source=None, version=None):
        return Document(doc_uri, source=source, version=version)

    def add_folder(self, folder):
        """
        :param WorkspaceFolder folder:
        """
        self._check_in_mutate_thread()
        folders = self._folders.copy()
        folders[folder.uri] = folder
        self._folders = folders

    def remove_folder(self, folder_uri):
        self._check_in_mutate_thread()
        folders = self._folders.copy()
        folders.pop(folder_uri, None)
        self._folders = folders

    @implements(IWorkspace.iter_documents)
    def iter_documents(self):
        self._check_in_mutate_thread()  # i.e.: we don't really mutate here, but this is not thread safe.
        return self._docs.values()

    @implements(IWorkspace.iter_folders)
    def iter_folders(self):
        return (
            self._folders.values()
        )  # Ok, thread-safe (folders are always set as a whole)

    @implements(IWorkspace.get_folder_paths)
    def get_folder_paths(self) -> List[str]:
        folders = self._folders  # Ok, thread-safe (folders are always set as a whole)
        return [uris.to_fs_path(ws_folder.uri) for ws_folder in folders.values()]

    @implements(IWorkspace.get_document)
    def get_document(self, doc_uri: str, accept_from_file: bool) -> Optional[IDocument]:
        # Ok, thread-safe (does not mutate the _docs dict -- contents in the _filesystem_docs
        # may end up stale or we may have multiple loads when we wouldn't need,
        # but that should be ok).
        doc = self._docs.get(doc_uri)
        if doc is not None:
            return doc

        if accept_from_file:
            doc = self._filesystem_docs.get(doc_uri)

            if doc is not None:
                if not doc.is_source_in_sync():
                    self._filesystem_docs.pop(doc_uri, None)
                    doc = None

            if doc is None:
                doc = self._create_document(doc_uri)
                try:
                    _source = doc.source  # Force loading current contents
                except:
                    # Unable to load contents: file does not exist.
                    doc = None
                else:
                    self._filesystem_docs[doc_uri] = doc

        return doc

    def is_local(self):
        # Thread-safe (only accesses immutable data).
        return (
            self._root_uri_scheme == "" or self._root_uri_scheme == "file"
        ) and os.path.exists(self._root_path)

    @implements(IWorkspace.put_document)
    def put_document(
        self, text_document: "robocorp_ls_core.lsp.TextDocumentItem"
    ) -> IDocument:
        self._check_in_mutate_thread()
        doc_uri = text_document.uri
        doc = self._docs[doc_uri] = self._create_document(
            doc_uri, source=text_document.text, version=text_document.version
        )
        try:
            # In case the initial text wasn't passed, try to load it from source.
            # If it doesn't work, set the initial source as empty.
            _source = doc.source
        except:
            doc.source = ""
        self._filesystem_docs.pop(doc_uri, None)
        return doc

    @implements(IWorkspace.remove_document)
    def remove_document(self, uri: str) -> None:
        self._check_in_mutate_thread()
        self._docs.pop(uri, None)

    @property
    def root_path(self):
        # Thread-safe (only accesses immutable data).
        return self._root_path

    @property
    def root_uri(self):
        # Thread-safe (only accesses immutable data).
        return self._root_uri

    def update_document(self, text_doc, change):
        """
        :param TextDocumentItem text_doc:
        :param TextDocumentContentChangeEvent change:
        """
        self._check_in_mutate_thread()
        doc_uri = text_doc["uri"]
        doc = self._docs[doc_uri]

        # Note: don't mutate an existing doc, always create a new one based on it
        # (so, existing references won't have racing conditions).
        new_doc = self._create_document(doc_uri, doc.source, text_doc["version"])
        new_doc.apply_change(change)
        self._docs[doc_uri] = new_doc

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

    def __init__(self, uri: str, source=None, version: Optional[str] = None):
        self._main_thread = threading.current_thread()

        self.uri = uri
        self.version = version
        self.path = uris.to_fs_path(uri)  # Note: may be None.

        self._source = source
        self.__line_start_offsets = None

        # Only set when the source is read from disk.
        self._source_mtime = -1

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

    def offset_to_line_col(self, offset):
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

    def get_last_line(self):
        try:
            last_line = self._lines[-1]
            if last_line.endswith("\r") or last_line.endswith("\n"):
                return ""
            return last_line
        except IndexError:
            return ""

    def get_last_line_col(self):
        lines = self._lines
        if not lines:
            return (0, 0)
        else:
            last_line = lines[-1]
            if last_line.endswith("\r") or last_line.endswith("\n"):
                return len(lines), 0
            return len(lines) - 1, len(last_line)

    def get_line_count(self):
        lines = self._lines
        return len(lines)

    def apply_change(self, change):
        """Apply a change to the document."""
        self._check_in_mutate_thread()
        text = change["text"]
        change_range = change.get("range")
        self._apply_change(change_range, text)

    def _apply_change(self, change_range, text):
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

    def apply_text_edits(self, text_edits):
        self._check_in_mutate_thread()
        for text_edit in reversed(text_edits):
            self._apply_change(text_edit["range"], text_edit["newText"])

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IDocument = check_implements(self)
