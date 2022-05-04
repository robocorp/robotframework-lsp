# Note: this is unused. Kept for posterity (maybe it'll turn out to be useful
# in the future).

import re
from pathlib import Path

method_names = [
    "textDocument/rename",
    "textDocument/prepareRename",
]


_RE_FIRST_CAP = re.compile("(.)([A-Z][a-z]+)")
_RE_ALL_CAP = re.compile("([a-z0-9])([A-Z])")


def _method_to_string(method):
    return _camel_to_underscore(method.replace("/", "__").replace("$", ""))


def _camel_to_underscore(string):
    s1 = _RE_FIRST_CAP.sub(r"\1_\2", string)
    return _RE_ALL_CAP.sub(r"\1_\2", s1).lower()


def replace_in_file(file_contents, new_contents):
    i = file_contents.find("# START CODEGEN")
    j = file_contents.find("# END CODEGEN")
    assert i >= 0
    assert j > 0
    start_contents = file_contents[: i + len("# START CODEGEN")]
    end_contents = file_contents[j:]

    # Get indent before START CODEGEN.
    start_line = max(start_contents.rfind("\r"), start_contents.rfind("\n")) + 1
    indent_i = 0
    for i in range(start_line, len(start_contents)):
        if start_contents[i] != " ":
            break
        indent_i += 1
    indent = " " * indent_i

    new_contents = ("\n" + indent).join(new_contents.splitlines(keepends=False))
    return start_contents + "\n" + indent + new_contents + "\n" + indent + end_contents


def codegen_declarations():
    rfls_file = (
        Path(__file__)
        / ".."
        / ".."
        / "src"
        / "robotframework_ls"
        / "robotframework_ls_impl.py"
    )
    assert rfls_file.exists()

    contents = rfls_file.read_text("utf-8")
    print(contents)

    new_contents = ["# fmt: off\n"]
    for name in method_names:
        method_name = f"def m_{_method_to_string(name)}(self, **kwargs):"
        new_contents.append(method_name)
        new_contents.append("\n")
    new_contents.append("# fmt: on\n")

    rfls_file.write_text(replace_in_file(contents, "".join(new_contents)), "utf-8")


def test():
    found = replace_in_file(
        """
    # START CODEGEN
    # END CODEGEN
""",
        "foobar",
    )

    assert (
        found.replace("\r\n", "\n").replace("\r", "\n")
        == """
    # START CODEGEN
    foobar
    # END CODEGEN
"""
    )

    found = replace_in_file(
        """
    # START CODEGEN
    # END CODEGEN
""",
        "foo\nbar",
    )

    assert (
        found.replace("\r\n", "\n").replace("\r", "\n")
        == """
    # START CODEGEN
    foo
    bar
    # END CODEGEN
"""
    )


if __name__ == "__main__":
    # test()
    codegen_declarations()
