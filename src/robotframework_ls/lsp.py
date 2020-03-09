# Original work Copyright 2017 Palantir Technologies, Inc. (MIT)
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
"""Some Language Server Protocol constants

https://github.com/Microsoft/language-server-protocol/blob/master/protocol.md
"""


class CompletionItemKind(object):
    Text = 1
    Method = 2
    Function = 3
    Constructor = 4
    Field = 5
    Variable = 6
    Class = 7
    Interface = 8
    Module = 9
    Property = 10
    Unit = 11
    Value = 12
    Enum = 13
    Keyword = 14
    Snippet = 15
    Color = 16
    File = 17
    Reference = 18


class DocumentHighlightKind(object):
    Text = 1
    Read = 2
    Write = 3


class DiagnosticSeverity(object):
    Error = 1
    Warning = 2
    Information = 3
    Hint = 4


class InsertTextFormat(object):
    PlainText = 1
    Snippet = 2


class MessageType(object):
    Error = 1
    Warning = 2
    Info = 3
    Log = 4


class SymbolKind(object):
    File = 1
    Module = 2
    Namespace = 3
    Package = 4
    Class = 5
    Method = 6
    Property = 7
    Field = 8
    Constructor = 9
    Enum = 10
    Interface = 11
    Function = 12
    Variable = 13
    Constant = 14
    String = 15
    Number = 16
    Boolean = 17
    Array = 18


class TextDocumentSyncKind(object):
    NONE = 0
    FULL = 1
    INCREMENTAL = 2


class _Base(object):
    def __getitem__(self, name):
        return getattr(self, name)

    def get(self, name, default=None):
        try:
            return getattr(self, name)
        except AttributeError:
            return default

    def to_dict(self):
        new_dict = {}
        for key, value in self.__dict__.items():
            if hasattr(value, "to_dict"):
                value = value.to_dict()
            new_dict[key] = value
        return new_dict


class TextEdit(_Base):
    def __init__(self, range, newText):
        """
        :param Range range:
        :param str new_text:
        """
        self.range = range
        self.newText = newText


class TextDocumentItem(_Base):
    def __init__(self, uri, languageId=None, version=None, text=None):
        """
        :param str uri:
        :param str language_id:
        :param int version:
        :param str text:
        """
        self.uri = uri
        self.languageId = languageId
        self.version = version
        self.text = text


class WorkspaceFolder(_Base):
    def __init__(self, uri, name):
        """
        :param str uri:
        :param str name:
        """
        self.uri = uri
        self.name = name


class CompletionItem(_Base):
    def __init__(
        self,
        label,
        kind=None,  # CompletionItemKind
        detail=None,
        documentation=None,  # str
        deprecated=False,
        preselect=False,
        sortText=None,  # str
        filterText=None,  # str
        insertText=None,  # str
        insertTextFormat=None,  # str
        text_edit=None,  # TextEdit
        additionalTextEdits=None,  # List['TextEdit']
        commitCharacters=None,  # List[str]
        command=None,  # Command
        data=None,
    ):
        self.label = label
        self.kind = kind
        self.detail = detail
        self.documentation = documentation
        self.deprecated = deprecated
        self.preselect = preselect
        self.sortText = sortText
        self.filterText = filterText
        self.insertText = insertText
        self.insertTextFormat = insertTextFormat
        self.textEdit = text_edit
        self.additionalTextEdits = additionalTextEdits
        self.commitCharacters = commitCharacters
        self.command = command
        self.data = data


class Position(_Base):
    def __init__(self, line=0, character=0):
        self.line = line
        self.character = character

    def __eq__(self, other):
        return (
            isinstance(other, Position)
            and self.line == other.line
            and self.character == other.character
        )

    def __ge__(self, other):
        line_gt = self.line > other.line

        if line_gt:
            return line_gt

        if self.line == other.line:
            return self.character >= other.character

        return False

    def __gt__(self, other):
        line_gt = self.line > other.line

        if line_gt:
            return line_gt

        if self.line == other.line:
            return self.character > other.character

        return False

    def __le__(self, other):
        line_lt = self.line < other.line

        if line_lt:
            return line_lt

        if self.line == other.line:
            return self.character <= other.character

        return False

    def __lt__(self, other):
        line_lt = self.line < other.line

        if line_lt:
            return line_lt

        if self.line == other.line:
            return self.character < other.character

        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "{}:{}".format(self.line, self.character)


class Range(_Base):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __eq__(self, other):
        return (
            isinstance(other, Range)
            and self.start == other.start
            and self.end == other.end
        )

    def __repr__(self):
        return "{}-{}".format(self.start, self.end)


class TextDocumentContentChangeEvent(_Base):
    def __init__(self, range, rangeLength, text):
        self.range = range
        self.rangeLength = rangeLength
        self.text = text


class LSPMessages(object):
    M_PUBLISH_DIAGNOSTICS = "textDocument/publishDiagnostics"
    M_APPLY_EDIT = "workspace/applyEdit"
    M_SHOW_MESSAGE = "window/showMessage"

    def __init__(self, endpoint):
        self._endpoint = endpoint

    def apply_edit(self, edit):
        return self._endpoint.request(self.M_APPLY_EDIT, {"edit": edit})

    def publish_diagnostics(self, doc_uri, diagnostics):
        self._endpoint.notify(
            self.M_PUBLISH_DIAGNOSTICS,
            params={"uri": doc_uri, "diagnostics": diagnostics},
        )

    def show_message(self, message, msg_type=MessageType.Info):
        self._endpoint.notify(
            self.M_SHOW_MESSAGE, params={"type": msg_type, "message": message}
        )
