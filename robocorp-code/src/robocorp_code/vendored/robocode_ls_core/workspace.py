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
from robocorp_ls_core.protocols import IWorkspace, IDocument
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.uris import uri_scheme, to_fs_path


log = get_logger(__name__)


class Workspace(object):
    def __init__(self, root_uri, workspace_folders=None) -> None:
        from robocorp_ls_core.lsp import WorkspaceFolder

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

        if root_uri and root_uri not in self.folders:
            as_fs_path = uris.to_fs_path(root_uri)
            name = os.path.basename(as_fs_path)
            self.add_folder(WorkspaceFolder(root_uri, name))

    def _create_document(self, doc_uri, source=None, version=None):
        return Document(doc_uri, source=source, version=version)

    def add_folder(self, folder):
        """
        :param WorkspaceFolder folder:
        """
        self._folders[folder.uri] = folder

    def remove_folder(self, folder_uri):
        self._folders.pop(folder_uri, None)

    def iter_documents(self):
        return self._docs.values()

    @property
    def folders(self):
        return self._folders

    @implements(IWorkspace.get_folder_paths)
    def get_folder_paths(self) -> List[str]:
        folders = self._folders
        return [uris.to_fs_path(ws_folder.uri) for ws_folder in folders.values()]

    @implements(IWorkspace.get_document)
    def get_document(self, doc_uri: str, accept_from_file: bool) -> Optional[IDocument]:
        doc = self._docs.get(doc_uri)
        if doc is None:
            if accept_from_file:
                doc = self._filesystem_docs.get(doc_uri)
                if doc is None:
                    doc = self._create_document(doc_uri)
                    self._filesystem_docs[doc_uri] = doc
                if not doc.sync_source():
                    self._filesystem_docs.pop(doc_uri, None)
                    doc = None

        return doc

    def is_local(self):
        return (
            self._root_uri_scheme == "" or self._root_uri_scheme == "file"
        ) and os.path.exists(self._root_path)

    @implements(IWorkspace.put_document)
    def put_document(
        self, text_document: "robocorp_ls_core.lsp.TextDocumentItem"
    ) -> IDocument:
        doc_uri = text_document.uri

        doc = self._docs[doc_uri] = self._create_document(
            doc_uri, source=text_document.text, version=text_document.version
        )
        self._filesystem_docs.pop(doc_uri, None)
        return doc

    @implements(IWorkspace.remove_document)
    def remove_document(self, uri: str) -> None:
        self._docs.pop(uri, None)

    @property
    def root_path(self):
        return self._root_path

    @property
    def root_uri(self):
        return self._root_uri

    def update_document(self, text_doc, change):
        """
        :param TextDocumentItem text_doc:
        :param TextDocumentContentChangeEvent change:
        """
        doc_uri = text_doc["uri"]
        doc = self._docs[doc_uri]
        doc.apply_change(change)
        doc.version = text_doc["version"]

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IWorkspace = check_implements(self)


class _LineInfo(object):
    def __init__(self):
        pass


class Document(object):
    def __init__(self, uri, source=None, version=None):
        self.uri = uri
        self.version = version
        self.path = uris.to_fs_path(uri)  # Note: may be None.

        self._source = source
        self.__line_start_offsets = None

        # Only set when the source is read from disk.
        self._source_mtime = -1

    def __str__(self):
        return str(self.uri)

    def __len__(self):
        return len(self.source)

    def __bool__(self):
        return True

    __nonzero__ = __bool__

    def selection(self, line, col):
        from robocorp_ls_core.document_selection import DocumentSelection

        return DocumentSelection(self, line, col)

    @property
    def _source(self):
        return self.__source

    @_source.setter
    def _source(self, source):
        # i.e.: when the source is set, reset the lines.
        self.__source = source
        self._clear_caches()

    def _clear_caches(self):
        self.__lines = None
        self.__line_start_offsets = None

    @property
    def _lines(self):
        if self.__lines is None:
            self.__lines = tuple(self.source.splitlines(True))
        return self.__lines

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
        if mtime is None:
            mtime = os.path.getmtime(self.path)

        self._source_mtime = mtime
        with io.open(self.path, "r", encoding="utf-8") as f:
            self._source = f.read()

    @implements(IDocument.sync_source)
    def sync_source(self):
        try:
            mtime = os.path.getmtime(self.path)
            if self._source_mtime != mtime:
                self._load_source(mtime)

            # Ok, we loaded the sources properly.
            return True
        except Exception:
            log.info("Unable to load source for: %s", self.path)
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
        text = change["text"]
        change_range = change.get("range")
        self._apply_change(change_range, text)

    def _apply_change(self, change_range, text):
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
        for text_edit in reversed(text_edits):
            self._apply_change(text_edit["range"], text_edit["newText"])
