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

from robocorp_ls_core.workspace import Document
from robocorp_ls_core.lsp import TextDocumentContentChangeEvent, Position, Range
from robocorp_ls_core import uris
import pytest
import os.path

DOC = """document
for
testing
"""
DOC_URI = uris.from_fs_path(os.path.abspath(__file__))


@pytest.fixture
def doc():
    return Document(DOC_URI, DOC)


def test_document_empty_edit():
    doc = Document("file:///uri", u"")
    change = TextDocumentContentChangeEvent(
        Range(Position(0, 0), Position(0, 0)), 0, u"f"
    )
    doc.apply_change(change)
    assert doc.source == u"f"


def test_document_end_of_file_edit():
    old = ["print 'a'\n", "print 'b'\n"]
    doc = Document("file:///uri", u"".join(old))

    change = TextDocumentContentChangeEvent(
        Range(Position(2, 0), Position(2, 0)), 0, u"o"
    )
    doc.apply_change(change)

    assert doc.get_internal_lines() == ("print 'a'\n", "print 'b'\n", "o")


def test_document_line_edit():
    doc = Document("file:///uri", u"itshelloworld")
    change = TextDocumentContentChangeEvent(
        Range(Position(0, 3), Position(0, 8)), 0, u"goodbye"
    )
    doc.apply_change(change)
    assert doc.source == u"itsgoodbyeworld"


def test_document_lines(doc):
    assert len(doc.get_internal_lines()) == 3
    assert doc.get_internal_lines()[0] == "document\n"


def test_document_multiline_edit():
    old = ["def hello(a, b):\n", "    print a\n", "    print b\n"]
    doc = Document("file:///uri", u"".join(old))
    change = TextDocumentContentChangeEvent(
        Range(Position(1, 4), Position(2, 11)), 0, u"print a, b"
    )
    doc.apply_change(change)

    assert doc.get_internal_lines() == ("def hello(a, b):\n", "    print a, b\n")


def test_document_props(doc):
    assert doc.uri == DOC_URI
    assert doc.source == DOC


def test_document_source_unicode():
    document_mem = Document(DOC_URI, u"my source")
    document_disk = Document(DOC_URI)
    assert isinstance(document_mem.source, type(document_disk.source))


def test_offset_at_position(doc):
    assert doc.selection(0, 8).offset_at_position == 8
    assert doc.selection(1, 5).offset_at_position == 14
    assert doc.selection(2, 0).offset_at_position == 13
    assert doc.selection(2, 4).offset_at_position == 17
    assert doc.selection(4, 0).offset_at_position == 21


def test_word_at_position(doc):
    """
    Return the position under the cursor (or last in line if past the end)
    """
    assert doc.selection(0, 8).word_at_column == "document"
    assert doc.selection(0, 1000).word_at_column == "document"
    assert doc.selection(1, 5).word_at_column == "for"
    assert doc.selection(2, 0).word_at_column == "testing"
    assert doc.selection(4, 0).word_at_column == ""


def test_word_to_cursor():
    """
    Return the position under the cursor (or last in line if past the end)
    """
    doc = Document("uri", "doc1 doc2")
    assert doc.selection(0, 0).word_to_column == ""
    assert doc.selection(0, 1).word_to_column == "d"
    assert doc.selection(0, 2).word_to_column == "do"
    assert doc.selection(0, 3).word_to_column == "doc"
    assert doc.selection(0, 4).word_to_column == "doc1"

    assert doc.selection(0, 5).word_to_column == ""
    assert doc.selection(0, 6).word_to_column == "d"
    assert doc.selection(0, 7).word_to_column == "do"
    assert doc.selection(0, 8).word_to_column == "doc"
    assert doc.selection(0, 9).word_to_column == "doc2"

    assert doc.selection(0, 10).word_to_column == "doc2"
    assert doc.selection(0, 11).word_to_column == "doc2"


def test_word_from_cursor():
    """
    Return the position under the cursor (or last in line if past the end)
    """
    doc = Document("uri", "doc1 doc2")
    assert doc.selection(0, 0).word_from_column == "doc1"
    assert doc.selection(0, 1).word_from_column == "oc1"
    assert doc.selection(0, 2).word_from_column == "c1"
    assert doc.selection(0, 3).word_from_column == "1"
    assert doc.selection(0, 4).word_from_column == ""

    assert doc.selection(0, 5).word_from_column == "doc2"
    assert doc.selection(0, 6).word_from_column == "oc2"
    assert doc.selection(0, 7).word_from_column == "c2"
    assert doc.selection(0, 8).word_from_column == "2"
    assert doc.selection(0, 9).word_from_column == ""

    assert doc.selection(0, 10).word_from_column == ""
    assert doc.selection(0, 11).word_from_column == ""


def test_get_line():
    d = Document(uri="", source="")
    assert d.get_last_line() == ""
    d.source = "my\nfoo"
    assert d.get_line(0) == "my"
    assert d.get_last_line() == "foo"
    assert d.get_line_count() == 2

    d.source = "my\nfoo\n"
    assert d.get_line(0) == "my"
    assert d.get_line(1) == "foo"
    assert d.get_line(2) == ""
    assert d.get_last_line() == ""

    assert list(d.iter_lines()) == ["my\n", "foo\n", ""]
    assert list(d.iter_lines(False)) == ["my", "foo", ""]


def test_get_last_line_col():
    d = Document(uri="", source="")
    assert d.get_last_line_col() == (0, 0)
    d.source = "my"
    assert d.get_last_line_col() == (0, 2)
    d.source = "my\n"
    assert d.get_last_line_col() == (1, 0)


def test_offset_to_line_col_1():
    d = Document(uri="", source="my\nfo\nba")
    assert d.offset_to_line_col(0) == (0, 0)
    assert d.offset_to_line_col(1) == (0, 1)
    assert d.offset_to_line_col(2) == (0, 2)

    assert d.offset_to_line_col(3) == (1, 0)
    assert d.offset_to_line_col(4) == (1, 1)
    assert d.offset_to_line_col(5) == (1, 2)

    assert d.offset_to_line_col(6) == (2, 0)
    assert d.offset_to_line_col(7) == (2, 1)
    assert d.offset_to_line_col(8) == (2, 2)

    # Note: block below is out of bounds
    assert d.offset_to_line_col(9) == (2, 3)
    assert d.offset_to_line_col(10) == (2, 4)


def test_offset_to_line_col_2():
    d = Document(uri="", source="\n\n\n")
    with pytest.raises(ValueError):
        assert d.offset_to_line_col(-1)

    assert d.offset_to_line_col(0) == (0, 0)
    assert d.offset_to_line_col(1) == (1, 0)
    assert d.offset_to_line_col(2) == (2, 0)

    # Note: block below is out of bounds
    assert d.offset_to_line_col(3) == (3, 0)
    assert d.offset_to_line_col(4) == (3, 1)
