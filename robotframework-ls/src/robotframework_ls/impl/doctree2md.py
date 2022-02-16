# Original work Copyright (c) 2012, C. G. Wrench <c.g.wrench@gmail.com>
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


# -*- coding: utf-8 -*-
"""Simple Markdown writer for reStructuredText.

See:

* https://daringfireball.net/projects/markdown/syntax
* https://guides.github.com/pdfs/markdown-cheatsheet-online.pdf
* https://github.com/matthew-brett/nb2plots/blob/master/nb2plots/doctree2md.py
"""
from __future__ import unicode_literals

import re
from textwrap import dedent
import posixpath

__docformat__ = "reStructuredText"

from docutils import frontend, nodes, writers, languages
from collections import OrderedDict


class IndentLevel(object):
    """Class to hold text being written for a certain indentation level

    For example, all text in list_elements need to be indented.  A list_element
    creates one of these indentation levels, and all text contained in the
    list_element gets written to this IndentLevel.  When we leave the
    list_element, we ``write`` the text with suitable prefixes to the next
    level down, which might be the base of the document (document body) or
    another indentation level, if this is - for example - a nested list.

    In most respects, IndentLevel behaves like a list.
    """

    def __init__(self, base, prefix, first_prefix=None):
        self.base = base  # The list to which we eventually write
        self.prefix = prefix  # Text prepended to lines
        # Text prepended to first list
        self.first_prefix = prefix if first_prefix is None else first_prefix
        # Our own list to which we append before doing a ``write``
        self.content = []

    def append(self, new):
        self.content.append(new)

    def __getitem__(self, index):
        return self.content[index]

    def __len__(self):
        return len(self.content)

    def __bool__(self):
        return len(self) != 0

    def write(self):
        """Add ``self.contents`` with current ``prefix`` and ``first_prefix``

        Add processed ``self.contents`` to ``self.base``.  The first line has
        ``first_prefix`` prepended, further lines have ``prefix`` prepended.

        Empty (all whitespace) lines get written as bare carriage returns, to
        avoid ugly extra whitespace.
        """
        string = "".join(self.content)
        lines = string.splitlines(True)
        if len(lines) == 0:
            return
        texts = [self.first_prefix + lines[0]]
        for line in lines[1:]:
            if line.strip() == "":  # avoid prefix for empty lines
                texts.append("\n")
            else:
                texts.append(self.prefix + line)
        self.base.append("".join(texts))


def _make_method(to_add):
    """Make a method that adds `to_add`

    We need this function so that `to_add` is a fresh and unique variable at
    the time the method is defined.
    """

    def method(self, node):
        self.add(to_add)

    return method


def add_pref_suff(pref_suff_map):
    """Decorator adds visit, depart methods for prefix/suffix pairs"""

    def dec(cls):
        # Need _make_method to ensure new variable picked up for each iteration
        # of the loop.  The defined method picks up this new variable in its
        # scope.
        for key, (prefix, suffix) in pref_suff_map.items():
            setattr(cls, "visit_" + key, _make_method(prefix))
            setattr(cls, "depart_" + key, _make_method(suffix))
        return cls

    return dec


def add_pass_thru(pass_thrus):
    """Decorator adds explicit pass-through visit and depart methods"""

    def meth(self, node):
        pass

    def dec(cls):
        for element_name in pass_thrus:
            for meth_prefix in ("visit_", "depart_"):
                meth_name = meth_prefix + element_name
                if hasattr(cls, meth_name):
                    raise ValueError("method name {} already defined".format(meth_name))
                setattr(cls, meth_name, meth)
        return cls

    return dec


# Characters that should be escaped in Markdown
ESCAPE_RE = re.compile(r"([\\*`])")

# Doctree elements for which Markdown element is <prefix><content><suffix>
PREF_SUFF_ELEMENTS = {
    "emphasis": ("*", "*"),  # Could also use ('_', '_')
    "strong": ("**", "**"),  # Could also use ('__', '__')
    "literal": ("`", "`"),
    "subscript": ("<sub>", "</sub>"),
    "superscript": ("<sup>", "</sup>"),
}

# Doctree elements explicitly passed through without extra markup
PASS_THRU_ELEMENTS = (
    "document",
    "container",
    "target",
    "inline",
    "definition_list",
    "definition_list_item",
    "term",
    "field_list",
    "field_list_item",
    "field",
    "field_name",
    "mpl_hint",
    "pending_xref",
    "compound",
)


@add_pass_thru(PASS_THRU_ELEMENTS)
@add_pref_suff(PREF_SUFF_ELEMENTS)
class Translator(nodes.NodeVisitor):

    std_indent = "    "

    def __init__(self, document, builder=None):
        nodes.NodeVisitor.__init__(self, document)
        self.builder = builder
        self.settings = settings = document.settings
        lcode = settings.language_code
        self.language = languages.get_language(lcode, document.reporter)
        # Not-None here indicates Markdown should use HTTP for internal and
        # download links.
        self.markdown_http_base = builder.markdown_http_base if builder else None
        # Warn only once per writer about unsupported elements
        self._warned = set()
        # Lookup table to get section list from name
        self._lists = OrderedDict((("head", []), ("body", []), ("foot", [])))
        # Reset attributes modified by reading
        self.reset()
        # Attribute shortcuts
        self.head, self.body, self.foot = self._lists.values()

    def reset(self):
        """Initialize object for fresh read"""
        for part in self._lists.values():
            part[:] = []

        # Current section heading level during writing
        self.section_level = 0

        # FIFO list of list prefixes, while writing nested lists.  Each element
        # corresponds to one level of nesting.  Thus ['1. ', '1. ', '* '] would
        # occur when writing items of an unordered list, that is nested within
        # an ordered list, that in turn is nested in another ordered list.
        self.list_prefixes = []

        # FIFO list of indentation levels.  When we are writing a block of text
        # that should be indented, we create a new indentation level.  We only
        # write the text when we leave the indentation level, so we can insert
        # the correct prefix for every line.
        self.indent_levels = []

        # Flag indicating we are processing docinfo items
        self._in_docinfo = False

        # Flag for whether to escape characters
        self._escape_text = True

    def astext(self):
        """Return the final formatted document as a string."""
        parts = ["".join(lines).strip() for lines in self._lists.values()]
        parts = [part + "\n\n" for part in parts if part]
        return "".join(parts).strip() + "\n"

    def ensure_eol(self):
        """Ensure the last line in current base is terminated by new line."""
        out = self.get_current_output()
        if out and out[-1] and out[-1][-1] != "\n":
            out.append("\n")

    def get_current_output(self, section="body"):
        """Get list or IndentLevel to which we are currently writing"""
        return self.indent_levels[-1] if self.indent_levels else self._lists[section]

    def add(self, string, section="body"):
        """Add `string` to `section` or current output

        Parameters
        ----------
        string : str
            String to add to output document
        section : {'body', 'head', 'foot'}, optional
            Section of document that generated text should be appended to, if
            not already appending to an indent level.  If already appending to
            an indent level, method will ignore `section`.  Use
            :meth:`add_section` to append to a section unconditionally.
        """
        self.get_current_output(section).append(string)

    def add_section(self, string, section="body"):
        """Add `string` to `section` regardless of current output

        Can be useful when forcing write to header or footer.

        Parameters
        ----------
        string : str
            String to add to output document
        section : {'body', 'head', 'foot'}, optional
            Section of document that generated text should be appended to.
        """
        self._lists[section].append(string)

    def start_level(self, prefix, first_prefix=None, section="body"):
        """Create a new IndentLevel with `prefix` and `first_prefix`"""
        base = (
            self.indent_levels[-1].content
            if self.indent_levels
            else self._lists[section]
        )
        level = IndentLevel(base, prefix, first_prefix)
        self.indent_levels.append(level)

    def finish_level(self):
        """Remove most recent IndentLevel and write contents"""
        level = self.indent_levels.pop()
        level.write()

    def escape_chars(self, txt):
        # Escape (some) characters with special meaning for Markdown
        return ESCAPE_RE.sub(r"\\\1", txt)

    def visit_Text(self, node):
        text = node.astext()
        if self._escape_text:
            text = self.escape_chars(text)
        self.add(text)

    def depart_Text(self, node):
        pass

    def visit_comment(self, node):
        txt = node.astext()
        if txt.strip():
            self.add("<!-- " + node.astext() + " -->\n")
        raise nodes.SkipNode

    def visit_docinfo(self, node):
        self._in_docinfo = True

    def depart_docinfo(self, node):
        self._in_docinfo = False

    def process_docinfo_item(self, node):
        """Called explicitly from methods in this class"""
        self.add_section("% {}\n".format(node.astext()), section="head")
        raise nodes.SkipNode

    def visit_definition(self, node):
        self.add("\n\n")
        self.start_level("    ", ":   ")

    def depart_definition(self, node):
        self.finish_level()

    visit_field_body = visit_definition

    depart_field_body = depart_definition

    def visit_paragraph(self, node):
        pass

    def depart_paragraph(self, node):
        self.ensure_eol()
        self.add("\n")

    def visit_math_block(self, node):
        # docutils math block
        self._escape_text = False
        self.add("$$\n")

    def depart_math_block(self, node):
        self._escape_text = True
        self.ensure_eol()
        self.add("$$\n\n")

    def visit_displaymath(self, node):
        # sphinx math blocks become displaymath
        self.add("$$\n{}\n$$\n\n".format(node["latex"]))
        raise nodes.SkipNode

    def visit_math(self, node):
        # sphinx math node has 'latex' attribute, docutils does not
        if "latex" in node:  # sphinx math node
            self.add("${}$".format(node["latex"]))
            raise nodes.SkipNode
        # docutils math node
        self._escape_text = False
        self.add("$")

    def depart_math(self, node):
        # sphinx node skipped in visit, only docutils gets here
        self._escape_text = True
        self.add("$")

    def visit_literal_block(self, node):
        self._escape_text = False
        if "code" in node["classes"]:  # Sphinx < 2
            if len(node["classes"]) > 1:
                code_type = node["classes"][1]
            else:
                code_type = ""
        else:  # Sphinx >= 2
            language = node.get("language", "")
            code_type = "" if language == "default" else language
        self.add("```" + code_type + "\n")

    def depart_literal_block(self, node):
        self._escape_text = True
        self.ensure_eol()
        self.add("```\n\n")

    def visit_doctest_block(self, node):
        self._escape_text = False
        self.add("```python\n")

    depart_doctest_block = depart_literal_block

    def visit_block_quote(self, node):
        self.start_level("> ")

    def depart_block_quote(self, node):
        self.finish_level()

    def visit_section(self, node):
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    def visit_enumerated_list(self, node):
        self.list_prefixes.append("1. ")

    def depart_enumerated_list(self, node):
        self.list_prefixes.pop()

    def visit_bullet_list(self, node):
        self.list_prefixes.append("* ")

    depart_bullet_list = depart_enumerated_list

    def visit_list_item(self, node):
        first_prefix = self.list_prefixes[-1]
        prefix = " " * len(first_prefix)
        self.start_level(prefix, first_prefix)

    def depart_list_item(self, node):
        self.finish_level()

    def visit_problematic(self, node):
        self.add("\n\n```\n{}\n```\n\n".format(node.astext()))
        raise nodes.SkipNode

    def visit_system_message(self, node):
        if node["level"] < self.document.reporter.report_level:
            # Level is too low to display
            raise nodes.SkipNode
        line = ", line %s" % node["line"] if node.hasattr("line") else ""
        self.add(
            "```\nSystem Message: {}:{}\n\n{}\n```\n\n".format(
                node["source"], line, node.astext()
            )
        )
        raise nodes.SkipNode

    def visit_title(self, node):
        self.add((self.section_level + 1) * "#" + " ")

    def depart_title(self, node):
        self.ensure_eol()
        self.add("\n")

    def visit_subtitle(self, node):
        self.add((self.section_level + 2) * "#" + " ")

    depart_subtitle = depart_title

    def visit_transition(self, node):
        # Simply replace a transition by a horizontal rule.
        # Could use three or more '*', '_' or '-'.
        self.add("\n---\n\n")
        raise nodes.SkipNode

    def _refuri2http(self, node):
        # Replace 'refuri' in reference with HTTP address, if possible
        # None for no possible address
        url = node.get("refuri")
        if not node.get("internal"):
            return url
        # If HTTP page build URL known, make link relative to that.
        if not self.markdown_http_base:
            return None
        this_doc = self.builder.current_docname
        if url in (None, ""):  # Reference to this doc
            url = self.builder.get_target_uri(this_doc)
        else:  # URL is relative to the current docname.
            this_dir = posixpath.dirname(this_doc)
            if this_dir:
                url = posixpath.normpath("{}/{}".format(this_dir, url))
        url = "{}/{}".format(self.markdown_http_base, url)
        if "refid" in node:
            url += "#" + node["refid"]
        return url

    def visit_reference(self, node):
        # If no target possible, pass through.
        url = self._refuri2http(node)
        if url is None:
            return
        self.add("[{0}]({1})".format(node.astext(), url))
        raise nodes.SkipNode

    def depart_reference(self, node):
        pass

    def visit_code_links(self, node):
        raise nodes.SkipNode

    def visit_index(self, node):
        # Drop index entries
        raise nodes.SkipNode

    def visit_substitution_definition(self, node):
        # Drop substitution definitions - the doctree already contains the text
        # with substitutions applied.
        raise nodes.SkipNode

    def visit_only(self, node):
        if node["expr"] == "markdown":
            self.add(dedent(node.astext()) + "\n")
        raise nodes.SkipNode

    def visit_runrole_reference(self, node):
        raise nodes.SkipNode

    def visit_download_reference(self, node):
        # If not resolving internal links, or there is no filename specified,
        # pass through.
        filename = node.get("filename")
        if None in (self.markdown_http_base, filename):
            return
        target_url = "{}/_downloads/{}".format(self.markdown_http_base, filename)
        self.add("[{}]({})".format(node.astext(), target_url))
        raise nodes.SkipNode

    def depart_download_reference(self, node):
        pass

    visit_compact_paragraph = visit_paragraph

    depart_compact_paragraph = depart_paragraph

    def unknown_visit(self, node):
        """Warn once per instance for unsupported nodes

        Intercept docinfo items if in docinfo block.
        """
        if self._in_docinfo:
            self.process_docinfo_item(node)
            return

        # Add as plain text on unknown.
        self.add(_escape_markdown(node.astext()))
        raise nodes.SkipNode

        # We really don't know this node type, warn once per node type
        # node_type = node.__class__.__name__
        # if node_type not in self._warned:
        #     self.document.reporter.warning(
        #         "The " + node_type + " element not yet supported in Markdown."
        #     )
        #     self._warned.add(node_type)


def _escape_markdown(text):
    if not text:
        return ""
    return (
        text.replace("_", r"\_")
        .replace("*", r"\*")
        .replace("[", r"\[")
        .replace("]", r"\]")
        .replace("#", r"\#")
    )


class Writer(writers.Writer):

    supported = ("markdown",)
    """Formats this writer supports."""

    output = None
    """Final translated form of `document`."""

    # Add configuration settings for additional Markdown flavours here.
    settings_spec = (
        "Markdown-Specific Options",
        None,
        (
            (
                "Extended Markdown syntax.",
                ["--extended-markdown"],
                {
                    "default": 0,
                    "action": "store_true",
                    "validator": frontend.validate_boolean,
                },
            ),
            (
                "Strict Markdown syntax. Default: true",
                ["--strict-markdown"],
                {
                    "default": 1,
                    "action": "store_true",
                    "validator": frontend.validate_boolean,
                },
            ),
        ),
    )

    translator_class = Translator

    def __init__(self, builder=None):
        writers.Writer.__init__(self)
        self.builder = builder

    def translate(self):
        visitor = self.translator_class(self.document, self.builder)
        self.document.walkabout(visitor)
        self.output = visitor.astext()
