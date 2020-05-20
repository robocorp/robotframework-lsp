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
import re


def md(html):
    from robotframework_ls import html_to_markdown

    return html_to_markdown.convert(html)


def test_html_to_markdown():
    assert md("<html><p>test</p><br></html>") == "test\n\n  \n"


def test_underscore():
    assert md("_hey_dude_") == r"\_hey\_dude\_"


def test_xml_entities():
    assert md("&amp;") == "&"


def test_named_entities():
    assert md("&raquo;") == "\xbb"


def test_hexadecimal_entities():
    # This looks to be a bug in BeautifulSoup (fixed in bs4) that we have to work around.
    assert md("&#x28;") == "\x28"
    assert md("&#x27;") == "\x27"


def test_single_escaping_entities():
    assert md("&amp;amp;") == "&amp;"


def test_single_tag():
    assert md("<span>Hello</span>") == "Hello"


def test_soup():
    assert md("<div><span>Hello</div></span>") == "Hello"


def test_whitespace():
    assert md(" a  b \n\n c ") == " a b c "


def test_a():
    assert md('<a href="http://google.com">Google</a>') == "[Google](http://google.com)"


def test_a_with_title():
    text = md('<a href="http://google.com" title="The &quot;Goog&quot;">Google</a>')
    assert text == r'[Google](http://google.com "The \"Goog\"")'


# def test_a_shortcut():
#     text = md('<a href="http://google.com">http://google.com</a>')
#     assert text == "<http://google.com>"


def test_a_no_autolinks():
    text = md('<a href="http://google.com">http://google.com</a>')
    assert text == "[http://google.com](http://google.com)"


def test_b():
    assert md("<b>Hello</b>") == "**Hello**"


def test_blockquote():
    assert md("<blockquote>Hello</blockquote>").strip() == "> Hello"


def test_nested_blockquote():
    text = md(
        "<blockquote>And she was like <blockquote>Hello</blockquote></blockquote>"
    ).strip()
    assert repr(text) == repr("> And she was like \n> > Hello")


def test_br():
    assert md("a<br />b<br />c") == "a  \nb  \nc"


def test_em():
    assert md("<em>Hello</em>") == "*Hello*"


def test_h1():
    assert md("<h1>Hello</h1>") == "Hello\n=====\n\n"


def test_h2():
    assert md("<h2>Hello</h2>") == "Hello\n-----\n\n"


def test_hn():
    assert md("<h3>Hello</h3>") == "### Hello\n\n"
    assert md("<h6>Hello</h6>") == "###### Hello\n\n"


def test_i():
    assert md("<i>Hello</i>") == "*Hello*"


def test_ol():
    assert repr(md("<ol><li>a</li><li>b</li></ol>")) == repr("1. a\n2. b\n")


def test_p():
    assert md("<p>hello</p>") == "hello\n\n"


def test_strong():
    assert md("<strong>Hello</strong>") == "**Hello**"


def test_ul():
    assert md("<ul><li>a</li><li>b</li></ul>") == "* a\n* b\n"


def test_li():
    assert md("<li>a</li><li>b</li>") == "- a\n- b\n"


nested_uls = re.sub(
    r"\s+",
    "",
    """
    <ul>
        <li>1
            <ul>
                <li>a
                    <ul>
                        <li>I</li>
                        <li>II</li>
                        <li>III</li>
                    </ul>
                </li>
                <li>b</li>
                <li>c</li>
            </ul>
        </li>
        <li>2</li>
        <li>3</li>
    </ul>""",
)


def test_nested_uls():
    """
    Nested ULs should alternate bullet characters.
    """
    txt = md(nested_uls)
    assert repr(txt) == repr(
        "* 1\n"
        "\t+ a\n"
        "\t\t- I\n"
        "\t\t- II\n"
        "\t\t- III\n"
        "\t\t\n"
        "\t+ b\n"
        "\t+ c\n"
        "\t\n"
        "* 2\n"
        "* 3\n"
    )


def test_img():
    assert (
        md('<img src="/path/to/img.jpg" alt="Alt text" title="Optional title" />')
        == '![Alt text](/path/to/img.jpg "Optional title")'
    )
    assert (
        md('<img src="/path/to/img.jpg" alt="Alt text" />')
        == "![Alt text](/path/to/img.jpg)"
    )


def test_nested():
    text = md('<p>This is an <a href="http://example.com/">example link</a>.</p>')
    assert text == "This is an [example link](http://example.com/).\n\n"


def test_div():
    assert md("<div>something. <strong>else</strong></div>") == "something. **else**"


def test_escape():
    assert md("<span>**escape** []#</span>") == r"\*\*escape\*\* \[\]\#"


def test_table():
    assert md("<table><tr><td>td1</td><td>td2</td></tr></table>") == "td1\ttd2\t\n\n"
