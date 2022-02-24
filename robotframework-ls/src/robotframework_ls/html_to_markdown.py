# Original work Copyright 2012-2018 Matthew Tretter (MIT)
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

# Note: port of https://github.com/matthewwithanm/python-markdownify using only
# the standard library (i.e.: html.parser).
import re
import logging
from functools import partial

log = logging.getLogger(__name__)

from html.parser import HTMLParser
from html.entities import name2codepoint

convert_heading_re = re.compile(r"convert_h(\d+)")
line_beginning_re = re.compile(r"^", re.MULTILINE)
whitespace_re = re.compile(r"[\r\n\s\t ]+")


def escape(text):
    if not text:
        return ""
    return (
        text.replace("_", r"\_")
        .replace("*", r"\*")
        .replace("[", r"\[")
        .replace("]", r"\]")
        .replace("#", r"\#")
    )


class _TagInfo(object):
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.output = []


class _HTMLToMarkdownParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.__output = []
        self.__tag = []
        self.__tag_info = []

        handlers = {}
        for d in dir(self):
            if d.startswith("_handle_"):
                handlers[d[8:]] = getattr(self, d)

        for i in range(10):
            handlers["h%s" % (i,)] = partial(self._handle_h, i)
        self._handlers = handlers

        # If we have something on start, check the start handlers too.
        handlers = {}
        for d in dir(self):
            if d.startswith("_start_handle_"):
                handlers[d[14:]] = getattr(self, d)

        self._start_handlers = handlers

    def handle_starttag(self, tag, attrs):
        # print("Start tag:", tag, type(tag))
        # for attr in attrs:
        #     print("     attr:", attr)

        if tag == "br":
            self._append("  \n")
            return

        elif tag in self._handlers:
            tag_info = _TagInfo(tag, attrs)
            self.__tag_info.append(tag_info)
            start_handler = self._start_handlers.get(tag)
            if start_handler is not None:
                start_handler(tag_info)

        self.__tag.append(tag)

    def handle_endtag(self, tag):
        # print("End tag  :", tag)

        if tag == "br":
            return

        else:
            handler = self._handlers.get(tag)
            if handler is not None:
                tag_info = self.__tag_info.pop()
                handler(tag_info)

        if self.__tag and self.__tag[-1] == tag:
            self.__tag.pop()

    def _extend(self, lst):
        output = self.__output
        if self.__tag_info:
            output = self.__tag_info[-1].output
        output.extend(lst)

    def _append(self, txt):
        output = self.__output
        if self.__tag_info:
            output = self.__tag_info[-1].output
        output.append(txt)

    def _handle_b(self, tag_info):
        if tag_info.output:
            self._append("**")
            self._extend(tag_info.output)
            self._append("**")

    _handle_strong = _handle_b

    def _handle_p(self, tag_info):
        self._extend(tag_info.output)
        self._append("\n\n")

    def _handle_a(self, tag_info):
        el = dict(tag_info.attrs)
        href = el.get("href")

        title = el.get("title")
        text = "".join(tag_info.output)

        # if text == href and not title:
        #     # Shortcut syntax
        #     self._append("<%s>" % href)
        # else:
        title_part = ' "%s"' % title.replace('"', r"\"") if title else ""

        if href.startswith("#"):
            if title:
                self._append("**%s**" % title.replace("*", r"\\*"))
            else:
                self._append("**%s**" % text.replace("*", r"\\*"))
            return

        self._append(
            "[%s](%s%s)" % (text or "", href, title_part) if href else text or ""
        )

    def _handle_img(self, tag_info):
        el = dict(tag_info.attrs)
        alt = el.get("alt", None) or ""
        src = el.get("src", None) or ""
        title = el.get("title", None) or ""
        title_part = ' "%s"' % title.replace('"', r"\"") if title else ""
        self._append("![")
        self._append(alt)
        self._append("](")
        self._append(src)
        self._append(title_part)
        self._append(")")

    def _handle_blockquote(self, tag_info):
        text = "".join(tag_info.output)

        self._append("\n")
        if text:
            self._append(line_beginning_re.sub("> ", text))

    def _handle_em(self, tag_info):
        if tag_info.output:
            self._append("*")
            self._extend(tag_info.output)
            self._append("*")

    _handle_i = _handle_em

    def _handle_table(self, tag_info):
        self._extend(tag_info.output)
        self._append("\n")

    def _handle_tr(self, tag_info):
        self._extend(tag_info.output)
        self._append("\n")

    def _handle_td(self, tag_info):
        self._extend(tag_info.output)
        self._append("\t")

    def _handle_h(self, n, tag_info):
        text = "".join(tag_info.output)
        text = text.rstrip()
        if n <= 2:
            line = "=" if n == 1 else "-"
            self._append(self.underline(text, line))
        else:
            hashes = "#" * n
            self._append("%s %s\n\n" % (hashes, text))

    def _handle_ol(self, tag_info):
        nested = False
        for parent_tag_info in self.__tag_info:
            if parent_tag_info.tag == "li":
                nested = True
        text = "".join(tag_info.output)
        if nested:
            text = "\n" + self.indent(text, 1)
        self._append(text)

    _handle_ul = _handle_ol

    def _handle_li(self, tag_info):
        try:
            parent_tag_info = self.__tag_info[-1]
        except:
            parent_tag_info = None

        if parent_tag_info is not None and parent_tag_info.tag == "ol":
            i_index_attr_name = "__i_index__"
            idx = getattr(parent_tag_info, i_index_attr_name, 0)
            bullet = "%s." % (idx + 1)
            setattr(parent_tag_info, i_index_attr_name, idx + 1)
        else:
            depth = -1
            for parent_tag_info in self.__tag_info:
                if parent_tag_info.tag == "ul":
                    depth += 1

            bullets = bullets = "*+-"
            try:
                bullet = bullets[depth % len(bullets)]
            except:
                bullet = "~"

        text = "".join(tag_info.output)
        self._append("%s %s\n" % (bullet, text))

    def indent(self, text, level):
        return line_beginning_re.sub("\t" * level, text) if text else ""

    def underline(self, text, pad_char):
        text = (text or "").rstrip()
        return "%s\n%s\n\n" % (text, pad_char * len(text)) if text else ""

    def handle_data(self, data):
        self._append(escape(whitespace_re.sub(" ", data or "")))
        # print("Data     :", data, type(data))

    def handle_comment(self, data):
        pass
        # print("Comment  :", data)

    def handle_entityref(self, name):
        try:
            c = chr(name2codepoint[name])
            self._append(c)
        except:
            log.exception("Error handling: %s", name)
        # print("Named ent:", c)

    def handle_charref(self, name):
        try:
            if name.startswith("x"):
                c = chr(int(name[1:], 16))
            else:
                c = chr(int(name))
            self._append(c)
        except:
            log.exception("Error handling: %s", name)
        # print("Num ent  :", c)

    def handle_decl(self, data):
        pass
        # print("Decl     :", data)

    def get_output(self):
        return "".join(self.__output)


def convert(html):
    parser = _HTMLToMarkdownParser()
    parser.feed(html)
    ret = parser.get_output()
    return ret
