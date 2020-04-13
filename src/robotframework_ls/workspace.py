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

from . import uris
from robotframework_ls.uris import uri_scheme, to_fs_path
from robotframework_ls.robotframework_log import get_logger

log = get_logger(__name__)


class Workspace(object):
    def __init__(self, root_uri, workspace_folders=None):
        self._root_uri = root_uri
        self._root_uri_scheme = uri_scheme(self._root_uri)
        self._root_path = to_fs_path(self._root_uri)
        self._folders = {}
        self._docs = {}

        if workspace_folders is not None:
            for folder in workspace_folders:
                self.add_folder(folder)

    def _create_document(self, doc_uri, source=None, version=None):
        return Document(doc_uri, source=source, version=version)

    def create_untracked_document(self, doc_uri):
        """
        Creates a document from an uri which points to the filesystem.
        
        The returned document is not referenced by the workspace and is
        not kept in sync afterwards (it's meant to be used and thrown away).
        
        The use-case is code completion referencing existing files (because
        right now if we get a document from the filesystem it's not kept in
        sync if changes happen in the filesystem -- after this is done, this
        API can be removed).
        
        :param str doc_uri:
            The uri for the document.
        """
        return self._create_document(doc_uri)

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

    def get_document(self, doc_uri, create=True):
        """
        Return a managed document if-present,
        else create one pointing at disk.

        See https://github.com/Microsoft/language-server-protocol/issues/177
        """
        doc = self._docs.get(doc_uri)
        if doc is None:
            if create:
                doc = self._create_document(doc_uri)

        return doc

    def is_local(self):
        return (
            self._root_uri_scheme == "" or self._root_uri_scheme == "file"
        ) and os.path.exists(self._root_path)

    def put_document(self, text_document):
        """
        :param TextDocumentItem text_document:
        """
        doc_uri = text_document.uri

        self._docs[doc_uri] = self._create_document(
            doc_uri, source=text_document.text, version=text_document.version
        )

    def remove_document(self, doc_uri):
        self._docs.pop(doc_uri, None)

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

    def __str__(self):
        return str(self.uri)

    def __len__(self):
        return len(self.source)

    def __bool__(self):
        return True

    __nonzero__ = __bool__

    def selection(self, line, col):
        from robotframework_ls.impl.completion_context import DocumentSelection

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

    @property
    def source(self):
        if self._source is None:
            with io.open(self.path, "r", encoding="utf-8") as f:
                self._source = f.read()
        return self._source

    @source.setter
    def source(self, source):
        self._source = source

    def get_line(self, line):
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
