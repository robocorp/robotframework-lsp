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
from typing import Optional
from robocorp_ls_core.protocols import Sentinel
from robotframework_ls.impl.protocols import ISymbolsCache


def markdown_doc(obj):
    """
    
    :type obj: LibraryDoc|KeywordDoc
    """
    if obj is None:
        return ""

    if not obj.doc:
        return ""

    if obj.doc_format.lower() == "html":
        try:
            return obj.__md_doc__
        except AttributeError:
            from robotframework_ls import html_to_markdown

            obj.__md_doc__ = html_to_markdown.convert(obj.doc)
        return obj.__md_doc__
    return obj.doc


def docs_and_format(obj):
    doc_format = obj.doc_format
    if doc_format.lower() == "html":
        return markdown_doc(obj), "markdown"
    return obj.doc, doc_format


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
    ):
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
        self._source = source
        self.lineno = lineno
        self.inits = []
        self.keywords = []

        self.symbols_cache: Optional[ISymbolsCache] = None

    @property
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


class KeywordArg(object):

    _is_keyword_arg = False
    _is_star_arg = False
    _default_value = None
    _arg_type = None

    def __init__(
        self, arg: str, name=Sentinel, arg_type=Sentinel, default_value=Sentinel
    ):
        """
        If arg_type and default_value are given, the arg name == arg, otherwise,
        the arg is expected to be something as 'arg:int=10' and thus the arg_type
        and default_value are computed.
        """
        self.original_arg = arg
        if arg.startswith("**"):
            self._is_keyword_arg = True
            arg = "&" + arg[2:]

        elif arg.startswith("*"):
            self._is_star_arg = True
            arg = "@" + arg[1:]

        else:
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
                colon_i = arg.rfind(":")
                if colon_i != -1:
                    self._arg_type = arg[colon_i + 1 :].strip()
                    arg = arg[:colon_i]

        if name is not Sentinel:
            self._arg_name = name
        else:
            self._arg_name = arg

    @property
    def arg_name(self) -> str:
        return self._arg_name

    @property
    def is_keyword_arg(self) -> bool:
        return self._is_keyword_arg

    @property
    def is_star_arg(self) -> bool:
        return self._is_star_arg

    @property
    def arg_type(self) -> Optional[str]:
        return self._arg_type

    @property
    def default_value(self) -> Optional[str]:
        return self._default_value


class KeywordDoc(object):
    def __init__(
        self, weak_libdoc, name="", args=(), doc="", tags=(), source=None, lineno=-1
    ):
        self._weak_libdoc = weak_libdoc
        self.name = name
        self._args = args
        self.doc = doc
        self.tags = tags
        self._source = source
        self.lineno = lineno

    @property
    def deprecated(self):
        return self.doc.startswith("*DEPRECATED") and "*" in self.doc[1:]

    @property
    @instance_cache
    def args(self):
        if self._args:
            if isinstance(self._args[0], KeywordArg):
                return self._args

        return tuple(KeywordArg(arg) for arg in self._args)

    @property
    @instance_cache
    def source(self):
        # When asked for, make sure that the path is absolute.
        source = self._source
        if source:
            if not os.path.isabs(source):
                libdoc = self._weak_libdoc()
                if libdoc is not None:
                    source = libdoc._make_absolute(source)
        return source

    @property
    def libdoc(self):
        return self._weak_libdoc()

    @property
    def doc_format(self):
        return self._weak_libdoc().doc_format

    def __repr__(self):
        return "KeywordDoc(%s, line: %s)" % (self.name, self.lineno)

    __str__ = __repr__


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
        if specversion == "3":
            libdoc.inits = self._create_keywords_v3(
                weakref.ref(libdoc), spec, "inits/init"
            )
            libdoc.keywords = self._create_keywords_v3(
                weakref.ref(libdoc), spec, "keywords/kw"
            )
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
    def _create_arguments_v3(self, elem):
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
                ret.append(KeywordArg(arg_repr))
                continue

            arg_type = arg.find("type")
            arg_default = arg.find("default")
            ret.append(
                KeywordArg(
                    arg_repr,
                    name,
                    arg_type.text if arg_type is not None else None,
                    arg_default.text if arg_default is not None else None,
                )
            )

        return ret

    def _create_keywords_v3(self, weak_libdoc, spec, path):
        ret = []
        for elem in spec.findall(path):
            ret.append(
                KeywordDoc(
                    weak_libdoc,
                    name=elem.get("name", ""),
                    args=tuple(self._create_arguments_v3(elem)),
                    doc=elem.find("doc").text or "",
                    tags=[t.text for t in elem.findall("tags/tag")],
                    source=elem.get("source"),
                    lineno=int(elem.get("lineno", -1)),
                )
            )
        return ret
