def check(initial, expected):
    from robotframework_ls import robot_to_markdown

    formatted = (
        robot_to_markdown.convert(initial).replace("\r\n", "\n").replace("\r", "\n")
    )
    expected = expected.replace("\r\n", "\n").replace("\r", "\n")
    if formatted != expected:
        print("Found: >>>")
        print(formatted)
        print("<<<")
        assert formatted == expected


def test_robot_to_markdown_table():
    initial = r"""The default log level can be given at library import time.

See `Valid log levels` section for information about available log
levels.

Examples:

| =Setting= |     =Value=    | =Value= |          =Comment=         |
| Library   | LoggingLibrary |         | # Use default level (INFO) |
| Library   | LoggingLibrary | DEBUG   | # Use the given level      |
"""

    expected = r"""The default log level can be given at library import time.


See `Valid log levels` section for information about available log levels.


Examples:


| Setting | Value | Value | Comment |
| :--- | :--- | :--- | :--- |
| Library | LoggingLibrary |  | \# Use default level (INFO) |
| Library | LoggingLibrary | DEBUG | \# Use the given level |

"""

    check(initial, expected)


def test_robot_to_markdown_table_2():
    initial = """Some *table* in docs
| =A= |  =B=  | = C =  |
| _1_ | Hello | world! |
| _2_ | Hi    |        |
"""

    expected = """Some **table** in docs


| A | B | C |
| :--- | :--- | :--- |
| *1* | Hello | world! |
| *2* | Hi |  |

"""

    check(initial, expected)


def test_robot_to_markdown_basic():
    initial = """
Example library in Robot Framework format.

- Formatting with *bold* and _italic_.
- URLs like http://example.com are turned to links.
- Custom links like [http://robotframework.org|Robot Framework] are supported.
- Linking to `My Keyword` works.
"""

    expected = """Example library in Robot Framework format.


- Formatting with **bold** and *italic*.
- URLs like [http://example.com](http://example.com) are turned to links.
- Custom links like [Robot Framework](http://robotframework.org) are supported.
- Linking to `My Keyword` works.

"""

    check(initial, expected)
