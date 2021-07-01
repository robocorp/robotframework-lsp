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
from __future__ import annotations
from typing import List, Union, Optional, Any
import typing

from robocorp_ls_core.protocols import IEndPoint, IFuture, TypedDict


class CompletionItemKind(object):
    User = 0
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
    Folder = 19
    EnumMember = 20
    Constant = 21
    Struct = 22
    Event = 23
    Operator = 24
    TypeParameter = 25
    Issue = 26


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


class FoldingRangeKind(object):
    COMMENT = "comment"
    IMPORTS = "imports"
    REGION = "region"


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
            if value.__class__ in (list, tuple):
                value = [v.to_dict() if hasattr(v, "to_dict") else v for v in value]
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
        insertTextFormat=None,  # int
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


class MarkupContent(_Base):
    def __init__(self, kind: "MarkupKind", value: str):
        self.kind = kind
        self.value = value


class ParameterInformation(_Base):
    def __init__(self, label: str, documentation: Union[str, MarkupContent] = None):
        self.label = label
        self.documentation = documentation


class SignatureInformation(_Base):
    def __init__(
        self,
        label: str,
        documentation: Union[str, MarkupContent] = None,
        parameters: List[ParameterInformation] = None,
    ):
        self.label = label
        self.documentation = documentation
        self.parameters = parameters


class SignatureHelp(_Base):
    def __init__(
        self,
        signatures: List[SignatureInformation],
        active_signature: int = 0,
        active_parameter: int = 0,
    ):
        self.signatures = signatures
        self.activeSignature = active_signature
        self.activeParameter = active_parameter


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


class PositionTypedDict(TypedDict):
    # Line position in a document (zero-based).
    line: int

    # Character offset on a line in a document (zero-based). Assuming that
    # the line is represented as a string, the `character` value represents
    # the gap between the `character` and `character + 1`.
    #
    # If the character value is greater than the line length it defaults back
    # to the line length.
    character: int


class RangeTypedDict(TypedDict):
    start: PositionTypedDict
    end: PositionTypedDict


class LocationTypedDict(TypedDict):
    uri: str
    range: RangeTypedDict


class SymbolInformationTypedDict(TypedDict, total=False):
    """
    :ivar location:
        The location of this symbol. The location's range is used by a tool
        to reveal the location in the editor. If the symbol is selected in the
        tool the range's start information is used to position the cursor. So
        the range usually spans more then the actual symbol's name and does
        normally include things like visibility modifiers.
        
        The range doesn't have to denote a node range in the sense of a abstract
        syntax tree. It can therefore not be used to re-construct a hierarchy of
        the symbols.

    :ivar containerName: 
        The name of the symbol containing this symbol. This information is for
        user interface purposes (e.g. to render a qualifier in the user interface
        if necessary). It can't be used to re-infer a hierarchy for the document
        symbols.
    """

    name: str
    kind: int  # SymbolKind value.
    location: LocationTypedDict
    containerName: Optional[str]


class TextDocumentTypedDict(TypedDict, total=False):
    uri: str
    languageId: Optional[str]
    version: Optional[int]
    text: Optional[str]


class MarkupContentTypedDict(TypedDict):
    kind: str  # "plaintext" | "markdown"
    value: str


class CompletionItemTypedDict(TypedDict, total=False):
    #
    # The label of this completion item. By default
    # also the text that is inserted when selecting
    # this completion.
    label: str
    #
    # The kind of this completion item. Based of the kind
    # an icon is chosen by the editor.
    kind: int  # CompletionItemKind
    #
    # Tags for this completion item.
    #
    # @since 3.15.0
    tags: Optional[Any]  # List[CompletionItemTag]
    #
    # A human-readable string with additional information
    # about this item, like type or symbol information.
    detail: Optional[str]
    #
    # A human-readable string that represents a doc-comment.
    documentation: Optional[Union[str, MarkupContentTypedDict]]
    #
    # Indicates if this item is deprecated.
    # @deprecated Use `tags` instead.
    deprecated: Optional[bool]
    #
    # Select this item when showing.
    #
    # *Note* that only one completion item can be selected and that the
    # tool / client decides which item that is. The rule is that the *first*
    # item of those that match best is selected.
    preselect: Optional[bool]
    #
    # A string that should be used when comparing this item
    # with other items. When `falsy` the [label](#CompletionItem.label)
    # is used.
    sortText: Optional[str]
    #
    # A string that should be used when filtering a set of
    # completion items. When `falsy` the [label](#CompletionItem.label)
    # is used.
    filterText: Optional[str]
    #
    # A string that should be inserted into a document when selecting
    # this completion. When `falsy` the [label](#CompletionItem.label)
    # is used.
    #
    # The `insertText` is subject to interpretation by the client side.
    # Some tools might not take the string literally. For example
    # VS Code when code complete is requested in this example `con<cursor position>`
    # and a completion item with an `insertText` of `console` is provided it
    # will only insert `sole`. Therefore it is recommended to use `textEdit` instead
    # since it avoids additional client side interpretation.
    insertText: Optional[str]
    #
    # The format of the insert text. The format applies to both the `insertText` property
    # and the `newText` property of a provided `textEdit`. If omitted defaults to
    # `InsertTextFormat.PlainText`.
    insertTextFormat: Optional[int]  # InsertTextFormat
    #
    # How whitespace and indentation is handled during completion
    # item insertion. If ignored the clients default value depends on
    # the `textDocument.completion.insertTextMode` client capability.
    #
    # @since 3.16.0
    insertTextMode: Optional[Any]  # InsertTextMode
    #
    # An [edit](#TextEdit) which is applied to a document when selecting
    # this completion. When an edit is provided the value of
    # [insertText](#CompletionItem.insertText) is ignored.
    #
    # Most editors support two different operation when accepting a completion item. One is to insert a
    # completion text and the other is to replace an existing text with a completion text. Since this can
    # usually not predetermined by a server it can report both ranges. Clients need to signal support for
    # `InsertReplaceEdits` via the `textDocument.completion.insertReplaceSupport` client capability
    # property.
    #
    # *Note 1:* The text edit's range as well as both ranges from a insert replace edit must be a
    # [single line] and they must contain the position at which completion has been requested.
    # *Note 2:* If an `InsertReplaceEdit` is returned the edit's insert range must be a prefix of
    # the edit's replace range, that means it must be contained and starting at the same position.
    #
    # @since 3.16.0 additional type `InsertReplaceEdit`
    textEdit: Optional[Any]  # Union[TextEdit, InsertReplaceEdit]
    #
    # An optional array of additional [text edits](#TextEdit) that are applied when
    # selecting this completion. Edits must not overlap (including the same insert position)
    # with the main [edit](#CompletionItem.textEdit) nor with themselves.
    #
    # Additional text edits should be used to change text unrelated to the current cursor position
    # (for example adding an import statement at the top of the file if the completion item will
    # insert an unqualified type).
    additionalTextEdits: Optional[List[TextEdit]]
    #
    # An optional set of characters that when pressed while this completion is active will accept it first and
    # then type that character. *Note* that all commit characters should have `length=1` and that superfluous
    # characters will be ignored.
    commitCharacters: Optional[List[str]]
    #
    # An optional [command](#Command) that is executed *after* inserting this completion. *Note* that
    # additional modifications to the current document should be described with the
    # [additionalTextEdits](#CompletionItem.additionalTextEdits)-property.
    command: Optional[Any]  # Command
    #
    # A data entry field that is preserved on a completion item between
    # a [CompletionRequest](#CompletionRequest) and a [CompletionResolveRequest]
    # (#CompletionResolveRequest)
    data: Optional[Any]


class HoverTypedDict(TypedDict, total=False):
    contents: MarkupContentTypedDict
    range: RangeTypedDict  # Optional


class ResponseErrorTypedDict(TypedDict, total=False):
    code: int
    message: str
    data: Any  # Optional


class ResponseTypedDict(TypedDict, total=False):
    id: Union[int, str, None]
    result: Any  # Optional
    error: ResponseErrorTypedDict  # Optional


class HoverResponseTypedDict(TypedDict, total=False):
    id: Union[int, str, None]
    result: HoverTypedDict  # Optional
    error: ResponseErrorTypedDict  # Optional


class CommandTypedDict(TypedDict, total=False):
    # Title of the command, like `save`.
    title: str

    # The identifier of the actual command handler.
    command: str

    # Arguments that the command handler should be
    # invoked with.
    arguments: Optional[list]


class DocumentSymbolTypedDict(TypedDict, total=False):

    # The name of this symbol. Will be displayed in the user interface and
    # therefore must not be an empty string or a string only consisting of
    # white spaces.
    name: str

    # More detail for this symbol, e.g the signature of a function.
    detail: Optional[str]

    # The kind of this symbol.
    kind: int  # SymbolKind

    # Tags for this document symbol.
    # @since 3.16.0
    tags: Optional[List[int]]

    # Indicates if this symbol is deprecated.
    # @deprecated Use tags instead
    deprecated: Optional[bool]

    # The range enclosing this symbol not including leading/trailing whitespace
    # but everything else like comments. This information is typically used to
    # determine if the clients cursor is inside the symbol to reveal in the
    # symbol in the UI.
    range: Range

    # The range that should be selected and revealed when this symbol is being
    # picked, e.g. the name of a function. Must be contained by the `range`.
    selectionRange: RangeTypedDict

    # Children of this symbol, e.g. properties of a class.
    children: Optional[list]  # Optional[List[DocumentSymbolTypedDict]]


class CodeLensTypedDict(TypedDict, total=False):

    # The range in which this code lens is valid. Should only span a single
    # line.
    range: RangeTypedDict

    # The command this code lens represents.
    command: Optional[CommandTypedDict]

    # A data entry field that is preserved on a code lens item between a code
    # lens and a code lens resolve request.
    data: Optional[Any]


class FoldingRangeTypedDict(TypedDict, total=False):
    """
    Represents a folding range. To be valid, start and end line must be bigger
    than zero and smaller than the number of lines in the document. Clients
    are free to ignore invalid ranges.
    """

    # The zero-based start line of the range to fold. The folded area starts
    # after the line's last character. To be valid, the end must be zero or
    # larger and smaller than the number of lines in the document.
    startLine: int

    # The zero-based character offset from where the folded range starts. If
    # not defined, defaults to the length of the start line.
    startCharacter: Optional[int]

    # The zero-based end line of the range to fold. The folded area ends with
    # the line's last character. To be valid, the end must be zero or larger
    # and smaller than the number of lines in the document.
    endLine: int

    # The zero-based character offset before the folded range ends. If not
    # defined, defaults to the length of the end line.
    endCharacter: Optional[int]

    # Describes the kind of the folding range such as `comment` or `region`.
    # The kind is used to categorize folding ranges and used by commands like
    # 'Fold all comments'. See [FoldingRangeKind](#FoldingRangeKind) for an
    # enumeration of standardized kinds.
    kind: Optional[str]


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

    @property
    def endpoint(self) -> IEndPoint:
        return self._endpoint

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
