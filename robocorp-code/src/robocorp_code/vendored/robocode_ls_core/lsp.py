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

https://github.com/microsoft/language-server-protocol/tree/gh-pages/_specifications
https://microsoft.github.io/language-server-protocol/specification
"""

from robocorp_ls_core.protocols import IEndPoint, IFuture
import typing


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


class MarkupKind(object):
    PlainText = "plaintext"
    Markdown = "markdown"


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
            if value is not None:
                new_dict[key] = value
        return new_dict

    def __repr__(self):
        import json

        return json.dumps(self.to_dict(), indent=4)


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
        documentationFormat=None,  # str
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
        self.documentationFormat = documentationFormat


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


class Range(_Base):
    def __init__(self, start, end):
        self.start = Position(*start) if start.__class__ in (list, tuple) else start
        self.end = Position(*end) if end.__class__ in (list, tuple) else end

    def __eq__(self, other):
        return (
            isinstance(other, Range)
            and self.start == other.start
            and self.end == other.end
        )

    def __ne__(self, other):
        return not (self == other)


class TextDocumentContentChangeEvent(_Base):
    def __init__(self, range, rangeLength, text):
        self.range = range
        self.rangeLength = rangeLength
        self.text = text


class LocationLink(_Base):
    def __init__(
        self, original_selection_range, target_uri, target_range, target_selection_range
    ):
        """
        :param original_selection_range:
            Span of the origin of this link.
            Used as the underlined span for mouse interaction. Defaults to the word range at
            the mouse position.
            
        :param target_uri:
            The target resource identifier of this link.
            
        :param target_range:
            The full target range of this link. If the target for example is a symbol then target range is the
            range enclosing this symbol not including leading/trailing whitespace but everything else
            like comments. This information is typically used to highlight the range in the editor.
            
        :param target_selection_range:
            The range that should be selected and revealed when this link is being followed, e.g the name of a function.
            Must be contained by the the `targetRange`. See also `DocumentSymbol#range`
        """
        self.originalSelectionRange = original_selection_range
        self.targetUri = target_uri
        self.targetRange = target_range
        self.targetSelectionRange = target_selection_range


class Location(_Base):
    def __init__(self, uri, range):
        """
        :param str uri:
        :param Range range:
        """
        self.uri = uri
        self.range = range


class LSPMessages(object):
    M_PUBLISH_DIAGNOSTICS = "textDocument/publishDiagnostics"
    M_APPLY_EDIT = "workspace/applyEdit"
    M_SHOW_MESSAGE = "window/showMessage"
    M_SHOW_MESSAGE_REQUEST = "window/showMessageRequest"

    def __init__(self, endpoint: IEndPoint):
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

    def show_message_request(
        self,
        message: str,
        actions: typing.List[typing.Dict[str, str]],
        msg_type=MessageType.Info,
    ) -> IFuture[typing.Optional[typing.Dict[str, str]]]:
        """
        :param message:
            The message to be shown.
        :param actions:
            A list of dicts where the key is 'title'.
        :param msg_type:
            The type of the message.
        :returns:
            One of the selected dicts in actions or None.
        """
        return self._endpoint.request(
            self.M_SHOW_MESSAGE_REQUEST,
            params={"type": msg_type, "message": message, "actions": actions},
        )


class Error(object):

    __slots__ = "msg start end".split(" ")

    def __init__(self, msg, start, end):
        """
        Note: `start` and `end` are tuples with (line, col).
        """
        self.msg = msg
        self.start = start
        self.end = end

    def to_dict(self):
        return dict((name, getattr(self, name)) for name in self.__slots__)

    def __repr__(self):
        import json

        return json.dumps(self.to_dict())

    __str__ = __repr__

    def to_lsp_diagnostic(self):
        return {
            "range": {
                "start": {"line": self.start[0], "character": self.start[1]},
                "end": {"line": self.end[0], "character": self.end[1]},
            },
            "severity": DiagnosticSeverity.Error,
            "source": "robotframework",
            "message": self.msg,
        }
