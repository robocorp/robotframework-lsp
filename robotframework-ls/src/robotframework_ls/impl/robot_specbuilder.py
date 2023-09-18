# Original work Copyright 2008-2015 Nokia Networks
# Original work Copyright 2016-2020 Robot Framework Foundation
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
import os
import weakref
from robocorp_ls_core.cache import instance_cache
from typing import Optional, Union, Type, Callable, List, Tuple
from robocorp_ls_core.protocols import Sentinel
from robotframework_ls.impl.protocols import ISymbolsCache, ILibraryDoc, IKeywordArg
from robocorp_ls_core.robotframework_log import get_logger, get_log_level
import json
import typing
import itertools
import inspect
from itertools import takewhile


log = get_logger(__name__)

_notified_missing_docutils = False


def getdoc(item):
    return inspect.getdoc(item) or ""


def getshortdoc(doc_or_item, linesep="\n"):
    if not doc_or_item:
        return ""

    from robotframework_ls.impl.robot_formatting.robot_normalizing import is_string

    doc = doc_or_item if is_string(doc_or_item) else getdoc(doc_or_item)
    lines = takewhile(lambda line: line.strip(), doc.splitlines())
    return linesep.join(lines)


def _rest_to_markdown(doc: str) -> Optional[str]:
    global _notified_missing_docutils
    try:
        import docutils.core
        from robotframework_ls.impl.doctree2md import Writer
    except Exception as e:
        if _notified_missing_docutils:
            return None

        if get_log_level() >= 2:
            log.exception(
                "It's not possible to convert rest to markdown (please make sure that `docutils` is installed)"
            )
        else:
            log.critical(
                "It's not possible to convert rest to markdown (please make sure that `docutils` is installed).\nOriginal error: %s",
                e,
            )

        _notified_missing_docutils = True
        return None

    return docutils.core.publish_string(
        doc,
        writer=Writer(),
        settings_overrides={
            "syntax_highlight": "none",
            "input_encoding": "unicode",
            "output_encoding": "unicode",
        },
    )


def _get_markdown_formatter(doc_format) -> Optional[Callable[[str], Optional[str]]]:
    lower_doc_format = doc_format.lower()
    if lower_doc_format == "robot":
        from robotframework_ls import robot_to_markdown

        return robot_to_markdown.convert

    if lower_doc_format == "html":
        from robotframework_ls import html_to_markdown

        return html_to_markdown.convert

    if lower_doc_format == "rest":
        return _rest_to_markdown

    return None


def _markdown_doc(lower_doc_format: str, obj) -> Optional[str]:
    """
    :type obj: LibraryDoc|KeywordDoc

    Note that None is returned if the conversion couldn't be done.
    """
    if not obj.doc:
        return ""

    if lower_doc_format in ("markdown", "md"):
        return obj.doc

    if lower_doc_format == "robot":
        try:
            return obj.__md_doc__
        except AttributeError:
            from robotframework_ls import robot_to_markdown

            obj.__md_doc__ = robot_to_markdown.convert(obj.doc)
        return obj.__md_doc__

    if lower_doc_format == "html":
        try:
            return obj.__md_doc__
        except AttributeError:
            from robotframework_ls import html_to_markdown

            obj.__md_doc__ = html_to_markdown.convert(obj.doc)
        return obj.__md_doc__

    if lower_doc_format == "rest":
        try:
            return obj.__md_doc__
        except AttributeError:
            obj.__md_doc__ = _rest_to_markdown(obj.doc)
        return obj.__md_doc__

    return None


def docs_and_format(obj):
    """
    Given an object with a '.doc_format' and a '.doc', provide a
    tuple with (formatted contents, MarkupKind)

    Where MarkupKind = 'plaintext' | 'markdown'

    Note: may create a `__md_doc__` cache in the object.
    """
    doc_format = obj.doc_format
    lower = doc_format.lower()

    if lower in ("robot", "html", "markdown", "rest"):
        try:
            as_markdown = _markdown_doc(lower, obj)
            if as_markdown is not None:
                return as_markdown, "markdown"

        except:
            log.exception("Error formatting: %s.\nContent:\n%s", lower, obj.doc)

    # Could be 'text' or 'rest' here...
    return obj.doc, "plaintext"


class LibraryDoc(object):
    def __init__(
        self,
        filename,
        name="",
        doc="",
        # This is the RobotFramework version.
        version="",
        # This is the version of the spec.
        specversion="",
        type="library",
        scope="",
        named_args=True,
        doc_format="",
        source=None,
        lineno=-1,
    ) -> None:
        assert filename
        self.filename = filename
        self.name = name
        self.doc = doc
        self.version = version
        self.specversion = specversion
        self.type = type
        self.scope = scope
        self.named_args = named_args
        self.doc_format = doc_format or "ROBOT"
        if source and source.startswith("<"):  # Deal with <string>
            source = None
        self._source = source
        self.lineno = lineno
        self.inits: list = []
        self.keywords: list = []
        self.data_types: list = []

        self.symbols_cache: Optional[ISymbolsCache] = None

    def to_dictionary(self):
        data_types = {}

        for data_type in self.data_types:
            type_name = data_type.type
            type_name = type_name[0].lower() + type_name[1:] + "s"
            # assert type_name in ("customs", "enums", "typedDicts")
            lst = data_types.setdefault(type_name, [])
            lst.append(data_type.to_dictionary())

        return {
            "name": self.name,
            "doc": self.doc,
            "version": self.version,
            "specversion": self.specversion,
            "type": self.type,
            "scope": self.scope,
            "docFormat": self.doc_format,
            "source": self._source,
            "lineno": self.lineno,
            "tags": list(self.all_tags),
            "inits": [init.to_dictionary() for init in self.inits],
            "keywords": [kw.to_dictionary() for kw in self.keywords],
            "dataTypes": data_types,
            "typedocs": [],
        }

    def copy(self):
        builder = JsonDocBuilder()
        spec = self.to_dictionary()
        filename = self.filename
        return builder.build_from_dict(filename, spec)

    @property  # type: ignore
    @instance_cache
    def source(self):
        # When asked for, make sure that the path is absolute.
        source = self._source
        if source:
            if not os.path.isabs(source):
                source = self._make_absolute(source)
        return source

    @instance_cache
    def _make_absolute(self, source):
        dirname = os.path.dirname(self.filename)
        return os.path.abspath(os.path.join(dirname, source))

    @property
    def doc_format(self):
        return self._doc_format

    @doc_format.setter
    def doc_format(self, doc_format):
        self._doc_format = doc_format or "ROBOT"

    @property
    def keywords(self):
        return self._keywords

    @keywords.setter
    def keywords(self, kws):
        self._keywords = sorted(kws, key=lambda kw: kw.name)

    @property
    def all_tags(self):
        from itertools import chain

        return tuple(chain.from_iterable(kw.tags for kw in self.keywords))

    def __repr__(self):
        return "LibraryDoc(%s, %s, keywords:%s)" % (
            self.filename,
            self.name,
            len(self.keywords),
        )

    __str__ = __repr__

    def convert_docs_to_html(self):
        from robotframework_ls.impl.robot_formatting.robot_html_utils import (
            DocFormatter,
        )
        from robotframework_ls.impl.robot_formatting.robot_html_utils import DocToHtml

        type_docs = ()  # TODO: We don't load this right now...

        formatter = DocFormatter(self.keywords, type_docs, self.doc, self.doc_format)
        self.doc = formatter.html(self.doc, intro=True)
        for item in self.inits + self.keywords:
            # If 'shortdoc' is not set, it is generated automatically based on 'doc'
            # when accessed. Generate and set it to avoid HTML format affecting it.
            item.shortdoc = item.shortdoc
            item.doc = formatter.html(item.doc)
        for type_doc in type_docs:
            # Standard docs are always in ROBOT format ...
            if type_doc.type == type_doc.STANDARD:
                # ... unless they have been converted to HTML already.
                if not type_doc.doc.startswith("<p>"):
                    type_doc.doc = DocToHtml("ROBOT")(type_doc.doc)
            else:
                type_doc.doc = formatter.html(type_doc.doc)
        self.doc_format = "HTML"

    def convert_docs_to_markdown(self) -> bool:
        old_doc_format = self.doc_format
        formatter = _get_markdown_formatter(old_doc_format)

        if formatter is not None:
            new_doc = formatter(self.doc)
            if new_doc is None:
                # We can't format it (docutils not installed?)
                return False

            self.doc = new_doc

            for item in itertools.chain(self.inits, self.keywords, self.data_types):
                new = formatter(item.doc)
                if new is not None:
                    item.doc = new

            self.doc_format = "markdown"

            return True

        return False


class KeywordArg(object):
    POSITIONAL_ONLY = "POSITIONAL_ONLY"
    POSITIONAL_ONLY_MARKER = "POSITIONAL_ONLY_MARKER"
    POSITIONAL_OR_NAMED = "POSITIONAL_OR_NAMED"
    VAR_POSITIONAL = "VAR_POSITIONAL"
    NAMED_ONLY_MARKER = "NAMED_ONLY_MARKER"
    NAMED_ONLY = "NAMED_ONLY"
    VAR_NAMED = "VAR_NAMED"

    _is_keyword_arg = False
    _is_star_arg = False
    _default_value: Union[Type[Sentinel], str] = Sentinel
    _arg_type: Union[Type[Sentinel], str] = Sentinel
    _arg_name: str

    def __init__(
        self,
        arg: str,
        name: Union[Type[Sentinel], str] = Sentinel,
        arg_type: Union[Type[Sentinel], str] = Sentinel,
        default_value: Union[Type[Sentinel], str] = Sentinel,
        kind: str = "",
    ):
        """
        If arg_type and default_value are given, the arg name == arg, otherwise,
        the arg is expected to be something as 'arg:int=10' and thus the arg_type
        and default_value are computed.
        """
        self.original_arg = arg
        self.kind = kind

        if arg.startswith("&"):
            self._is_keyword_arg = True
            if not kind:
                self.kind = self.VAR_NAMED

        elif arg.startswith("@"):
            self._is_star_arg = True
            if not kind:
                self.kind = self.VAR_POSITIONAL

        elif arg.startswith("**"):
            self._is_keyword_arg = True
            arg = "&" + arg[2:]
            if not kind:
                self.kind = self.VAR_NAMED

        elif arg.startswith("*"):
            self._is_star_arg = True
            arg = "@" + arg[1:]
            if not kind:
                self.kind = self.VAR_POSITIONAL

        else:
            if not kind:
                self.kind = self.POSITIONAL_OR_NAMED

            if default_value is not Sentinel:
                self._default_value = default_value
            else:
                eq_i = arg.rfind("=")
                if eq_i != -1:
                    self._default_value = arg[eq_i + 1 :].strip()
                    arg = arg[:eq_i]

            if arg_type is not Sentinel:
                self._arg_type = arg_type
            else:
                if default_value is not Sentinel:
                    # i.e.: if the default value was given this was already
                    # done when we got here.
                    eq_i = arg.rfind("=")
                    if eq_i != -1:
                        arg = arg[:eq_i].strip()

                colon_i = arg.rfind(":")
                if colon_i != -1:
                    self._arg_type = arg[colon_i + 1 :].strip()
                    arg = arg[:colon_i]

        if name is not Sentinel:
            self._arg_name = typing.cast(str, name)
        else:
            self._arg_name = arg

    def to_dictionary(self):
        ret = {
            "name": self._arg_name,
            "kind": self.kind,
            "repr": self.original_arg,
            "required": True,
        }
        if self._default_value is not Sentinel:
            ret["defaultValue"] = self._default_value
        else:
            ret["defaultValue"] = None

        if self._arg_type is not Sentinel:
            arg_type = self._arg_type
            if not isinstance(arg_type, (list, tuple)):
                arg_type = [arg_type]
            ret["types"] = arg_type
        else:
            ret["types"] = []
        ret["typedocs"] = []

        return ret

    def is_default_value_set(self) -> bool:
        return self._default_value is not Sentinel

    @property
    def arg_name(self) -> str:
        return self._arg_name

    @property
    def is_keyword_arg(self) -> bool:
        return self._is_keyword_arg

    @property
    def is_star_arg(self) -> bool:
        return self._is_star_arg

    def is_arg_type_set(self) -> bool:
        return self._arg_type is not Sentinel

    @property
    def arg_type(self) -> Optional[str]:
        if self._arg_type is Sentinel:
            return None
        return typing.cast(Optional[str], self._arg_type)

    @property
    def default_value(self) -> Optional[str]:
        if self._default_value is Sentinel:
            return None
        return typing.cast(Optional[str], self._default_value)

    def __repr__(self):
        return f"KeywordArg({self.original_arg})"

    __str__ = __repr__


class KeywordDoc(object):
    def __init__(
        self, weak_libdoc, name="", args=(), doc="", tags=(), source=None, lineno=-1
    ):
        self._weak_libdoc = weak_libdoc
        self.name = name
        self._args = args
        self.doc = doc
        self.tags = tags
        self._shortdoc = ""
        if source and source.startswith("<"):
            source = None
        self._source = source
        self.lineno = lineno

    @property
    def shortdoc(self):
        return self._shortdoc or self._doc_to_shortdoc()

    def _doc_to_shortdoc(self):
        doc_format = self.doc_format
        if doc_format == "HTML":
            from robotframework_ls.impl.robot_formatting.robot_html_utils import (
                HtmlToText,
            )

            doc = HtmlToText().get_shortdoc_from_html(self.doc)
        else:
            doc = self.doc
        return " ".join(getshortdoc(doc).splitlines())

    @shortdoc.setter  # type: ignore
    def shortdoc(self, shortdoc):
        self._shortdoc = shortdoc

    @property
    def deprecated(self) -> bool:
        from robotframework_ls.impl.text_utilities import has_deprecated_text

        return has_deprecated_text(self.doc)

    @property  # type: ignore
    @instance_cache
    def args(self) -> Tuple[IKeywordArg, ...]:
        if self._args:
            if isinstance(self._args[0], KeywordArg):
                return self._args

        return tuple(KeywordArg(arg) for arg in self._args)

    @property  # type: ignore
    @instance_cache
    def source(self) -> str:
        # When asked for, make sure that the path is absolute.
        source = self._source
        if source:
            if not os.path.isabs(source):
                libdoc = self._weak_libdoc()
                if libdoc is not None:
                    source = libdoc._make_absolute(source)
        return source

    @property
    def libdoc(self) -> ILibraryDoc:
        return self._weak_libdoc()

    @property
    def doc_format(self) -> str:
        return self._weak_libdoc().doc_format

    def __repr__(self):
        return "KeywordDoc(%s, line: %s)" % (self.name, self.lineno)

    __str__ = __repr__

    def to_dictionary(self) -> dict:
        return {
            "name": self.name,
            "args": [arg.to_dictionary() for arg in self.args],
            "doc": self.doc,
            "tags": list(self.tags),
            "source": self.source,
            "shortdoc": self.shortdoc,
            "lineno": self.lineno,
        }

    def __typecheckself__(self) -> None:
        from robotframework_ls.impl.protocols import IKeywordDoc
        from robocorp_ls_core.protocols import check_implements

        _: IKeywordDoc = check_implements(self)


class DataType(object):
    type: str = ""

    def __init__(self, name, doc):
        self.name = name
        self.doc = doc

    def to_dictionary(self):
        return {
            "type": self.type,
            "name": self.name,
            "doc": self.doc,
        }


class TypedDictDoc(DataType):
    type = "TypedDict"

    def __init__(self, name, doc, items=None):
        super().__init__(name, doc)
        self.items = items or []

    def to_dictionary(self):
        return {
            "type": self.type,
            "name": self.name,
            "doc": self.doc,
            "items": self.items,
        }


class EnumDoc(DataType):
    type = "Enum"

    def __init__(self, name, doc, members=None):
        super().__init__(name, doc)
        self.members = members or []

    def to_dictionary(self):
        return {
            "type": self.type,
            "name": self.name,
            "doc": self.doc,
            "members": self.members,
        }


class CustomDoc(DataType):
    type = "Custom"


class SpecDocBuilder(object):
    def build(self, path):
        spec = self._parse_spec(path)

        version = spec.find("version")
        specversion = spec.get("specversion")

        libdoc = LibraryDoc(
            path,
            name=spec.get("name"),
            type=spec.get("type"),
            version=version.text if version is not None else "",
            specversion=specversion if specversion is not None else "",
            doc=spec.find("doc").text or "",
            scope=self._get_scope(spec),
            named_args=self._get_named_args(spec),
            doc_format=spec.get("format", "ROBOT"),
            source=spec.get("source"),
            lineno=int(spec.get("lineno", -1)),
        )

        try:
            specversion = int(specversion)
        except:
            log.exception(f"Error converting specversion: {specversion} to an int.")
            specversion = 0  # Too old?

        if specversion >= 3:
            libdoc.inits = self._create_keywords_v3(
                weakref.ref(libdoc), spec, "inits/init", specversion
            )
            libdoc.keywords = self._create_keywords_v3(
                weakref.ref(libdoc), spec, "keywords/kw", specversion
            )
            try:
                libdoc.data_types = self._create_data_types(spec)
            except:
                log.exception("Error loading data types from libspec.")
        else:
            libdoc.inits = self._create_keywords_v2(weakref.ref(libdoc), spec, "init")
            libdoc.keywords = self._create_keywords_v2(weakref.ref(libdoc), spec, "kw")
        return libdoc

    def _get_scope(self, spec):
        # RF >= 3.2 has "scope" attribute w/ value 'GLOBAL', 'SUITE, or 'TEST'.
        if "scope" in spec.attrib:
            return spec.get("scope")
        # RF < 3.2 has "scope" element. Need to map old values to new.
        scope = spec.find("scope").text
        return {
            "": "GLOBAL",  # Was used with resource files.
            "global": "GLOBAL",
            "test suite": "SUITE",
            "test case": "TEST",
        }[scope]

    def _create_data_types(self, spec):
        data_types = [
            self._create_enum_doc(dt) for dt in spec.findall("datatypes/enums/enum")
        ]
        data_types.extend(
            self._create_typed_dict_doc(dt)
            for dt in spec.findall("datatypes/typeddicts/typeddict")
        )
        data_types.extend(
            self._create_custom_doc(dt)
            for dt in spec.findall("datatypes/customs/custom")
        )
        return data_types

    def _create_enum_doc(self, dt):
        return EnumDoc(
            name=dt.get("name"),
            doc=dt.find("doc").text or "",
            members=[
                {"name": member.get("name"), "value": member.get("value")}
                for member in dt.findall("members/member")
            ],
        )

    def _create_typed_dict_doc(self, dt):
        items = []
        for item in dt.findall("items/item"):
            required = item.get("required", None)
            if required is not None:
                required = True if required == "true" else False
            items.append(
                {"key": item.get("key"), "type": item.get("type"), "required": required}
            )
        return TypedDictDoc(
            name=dt.get("name"), doc=dt.find("doc").text or "", items=items
        )

    def _create_custom_doc(self, dt):
        return CustomDoc(name=dt.get("name"), doc=dt.find("doc").text or "")

    def _parse_spec(self, path):
        try:
            from xml.etree import cElementTree as ET
        except ImportError:
            from xml.etree import ElementTree as ET

        if not os.path.isfile(path):
            raise IOError("Spec file '%s' does not exist." % path)
        root = ET.parse(path).getroot()
        if root.tag != "keywordspec":
            raise RuntimeError("Invalid spec file '%s'." % path)
        return root

    def _get_named_args(self, spec):
        elem = spec.find("namedargs")
        if elem is None:
            return False  # Backwards compatiblity with RF < 2.6.2
        return elem.text == "yes"

    # ===========================================================================
    # V2 handling
    # ===========================================================================
    def _create_keywords_v2(self, weak_libdoc, spec, path):
        ret = []
        for elem in spec.findall(path):
            args = []
            for a in elem.findall("arguments/arg"):
                if a.text == "*":
                    continue
                args.append(a.text)
            ret.append(
                KeywordDoc(
                    weak_libdoc,
                    name=elem.get("name", ""),
                    args=tuple(args),
                    doc=elem.find("doc").text or "",
                    tags=tuple(t.text for t in elem.findall("tags/tag")),
                    source=elem.get("source"),
                    lineno=int(elem.get("lineno", -1)),
                )
            )
        return ret

    # ===========================================================================
    # V3 handling
    # ===========================================================================
    def _create_arguments_v3(self, elem, specversion):
        ret = []
        for arg in elem.findall("arguments/arg"):
            name = arg.find("name")
            if name is None:
                continue
            name = name.text

            arg_repr = arg.get("repr")
            if not arg_repr:
                arg_repr = name

            kind = arg.get("kind")
            if not kind or kind in ("VAR_POSITIONAL", "VAR_NAMED"):
                # Default handling for *args and **kwargs converts to &args / @args
                ret.append(KeywordArg(arg_repr, kind=kind))
                continue

            arg_type = arg.find("type")
            if arg_type is None:
                use_arg_type = Sentinel
            else:
                if specversion >= 6:
                    # In version 6 onwards the type is actually something as:
                    # <type name="int" typedoc="integer"/>
                    use_arg_type = arg_type.get("name")
                else:
                    use_arg_type = arg_type.text

            arg_default = arg.find("default")
            ret.append(
                KeywordArg(
                    arg_repr,
                    name,
                    use_arg_type,
                    arg_default.text if arg_default is not None else Sentinel,
                    kind=kind,
                )
            )

        return ret

    def _create_keywords_v3(self, weak_libdoc, spec, path, specversion):
        ret = []
        for elem in spec.findall(path):
            ret.append(
                KeywordDoc(
                    weak_libdoc,
                    name=elem.get("name", ""),
                    args=tuple(self._create_arguments_v3(elem, specversion)),
                    doc=elem.find("doc").text or "",
                    tags=[t.text for t in elem.findall("tags/tag")],
                    source=elem.get("source"),
                    lineno=int(elem.get("lineno", -1)),
                )
            )
        return ret


class JsonDocBuilder:
    def build(self, path):
        assert isinstance(path, str)
        spec = self._parse_spec_json(path)
        return self.build_from_dict(path, spec)

    def build_from_stream(self, spec_filename, stream):
        spec = json.loads(stream.read())
        return self.build_from_dict(spec_filename, spec)

    def build_from_dict(self, filename, spec):
        libdoc = LibraryDoc(
            filename,
            name=spec["name"],
            doc=spec["doc"],
            version=spec["version"],
            specversion=spec["specversion"],
            type=spec["type"],
            scope=spec["scope"],
            doc_format=spec["docFormat"],
            source=spec["source"],
            lineno=int(spec.get("lineno", -1)),
        )
        new_data_types = []

        for custom in spec["dataTypes"].get("customs", []):
            new_data_types.append(
                CustomDoc(
                    name=custom["name"],
                    doc=custom["doc"],
                )
            )

        for enum in spec["dataTypes"].get("enums", []):
            new_data_types.append(
                EnumDoc(
                    name=enum["name"],
                    doc=enum["doc"],
                    members=enum["members"],
                )
            )
        for typed_dict in spec["dataTypes"].get("typedDicts", []):
            new_data_types.append(
                TypedDictDoc(
                    name=typed_dict["name"],
                    doc=typed_dict["doc"],
                    items=typed_dict["items"],
                )
            )

        libdoc.data_types = new_data_types

        weak_libdoc = weakref.ref(libdoc)
        libdoc.inits = [self._create_keyword(kw, weak_libdoc) for kw in spec["inits"]]
        libdoc.keywords = [
            self._create_keyword(kw, weak_libdoc) for kw in spec["keywords"]
        ]
        return libdoc

    def _parse_spec_json(self, path):
        if not os.path.isfile(path):
            raise RuntimeError("Spec file '%s' does not exist." % path)
        with open(path) as json_source:
            libdoc_dict = json.load(json_source)
        return libdoc_dict

    def _create_keyword(self, kw, weak_libdoc):
        return KeywordDoc(
            name=kw.get("name"),
            args=self._create_arguments(kw["args"]),
            doc=kw["doc"],
            tags=kw["tags"],
            source=kw["source"],
            lineno=int(kw.get("lineno", -1)),
            weak_libdoc=weak_libdoc,
        )

    def _create_arguments(self, arguments) -> List[KeywordArg]:
        new_arguments = []

        for argument in arguments:
            arg = argument["repr"]
            name = argument["name"]
            kind = argument["kind"]

            kwargs = {
                "arg": arg,
                "name": name,
                "kind": kind,
            }

            arg_type = argument.get("types")
            if arg_type is not None:
                kwargs["arg_type"] = arg_type

            default_value = argument.get("defaultValue")
            if default_value is not None:
                kwargs["default_value"] = default_value
            new_arguments.append(KeywordArg(**kwargs))

        return new_arguments
