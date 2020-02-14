# Copyright 2017 Palantir Technologies, Inc.
# License: MIT
import io
import logging
import os

from . import uris

log = logging.getLogger(__name__)


class Workspace(object):
    def __init__(self, root_uri, endpoint, config=None):
        self._root_uri = root_uri
        self._endpoint = endpoint
        self._root_uri_scheme = uris.urlparse(self._root_uri)[0]
        self._root_path = uris.to_fs_path(self._root_uri)
        self._docs = {}

    @property
    def documents(self):
        return self._docs

    @property
    def root_path(self):
        return self._root_path

    @property
    def root_uri(self):
        return self._root_uri

    def is_local(self):
        return (
            self._root_uri_scheme == "" or self._root_uri_scheme == "file"
        ) and os.path.exists(self._root_path)

    def get_document(self, doc_uri):
        """Return a managed document if-present, else create one pointing at disk.

        See https://github.com/Microsoft/language-server-protocol/issues/177
        """
        return self._docs.get(doc_uri) or self._create_document(doc_uri)

    def put_document(self, doc_uri, source, version=None):
        self._docs[doc_uri] = self._create_document(
            doc_uri, source=source, version=version
        )

    def rm_document(self, doc_uri):
        self._docs.pop(doc_uri)

    def update_document(self, doc_uri, change, version=None):
        self._docs[doc_uri].apply_change(change)
        self._docs[doc_uri].version = version

    def _create_document(self, doc_uri, source=None, version=None):
        return Document(doc_uri, source=source, version=version)


class Document(object):
    def __init__(self, uri, source=None, version=None):
        self.uri = uri
        self.version = version
        self.path = uris.to_fs_path(uri)

        self._source = source
        self._lines = None

    def __str__(self):
        return str(self.uri)

    def __len__(self):
        return len(self.source)

    def selection(self, line, col):
        from robotframework_ls.impl.completion_context import DocumentSelection

        return DocumentSelection(self, line, col)

    @property
    def _source(self):
        return self.__source

    @_source.setter
    def _source(self, source):
        # i.e.: when the source is set, reset the lines.
        self._lines = None
        self.__source = source

    @property
    def lines(self):
        if self._lines is None:
            self._lines = tuple(self.source.splitlines(True))
        return self._lines

    @property
    def source(self):
        if self._source is None:
            with io.open(self.path, "r", encoding="utf-8") as f:
                return f.read()
        return self._source

    def apply_change(self, change):
        """Apply a change to the document."""
        text = change["text"]
        change_range = change.get("range")

        if not change_range:
            # The whole file has changed

            self._source = text
            return

        start_line = change_range["start"]["line"]
        start_col = change_range["start"]["character"]
        end_line = change_range["end"]["line"]
        end_col = change_range["end"]["character"]

        # Check for an edit occurring at the very end of the file
        if start_line == len(self.lines):

            self._source = self.source + text
            return

        new = io.StringIO()

        # Iterate over the existing document until we hit the edit range,
        # at which point we write the new text, then loop until we hit
        # the end of the range and continue writing.
        for i, line in enumerate(self.lines):
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
