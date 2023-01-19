from robocorp_ls_core.lsp import TextEdit
from typing import List
from robocorp_ls_core.protocols import IDocument


def robot_source_format(source, space_count=4):
    if not source.strip():
        return None

    from robot.tidy import Tidy

    t = Tidy(space_count=space_count)
    from io import StringIO

    s = StringIO()
    if isinstance(source, bytes):
        source = source.decode("utf-8", "replace")

    s.write(source)
    s.seek(0)
    formatted = t.file(s)
    if not formatted:
        return None

    return formatted


def _create_range(d: IDocument, offset1: int, offset2: int):
    from robocorp_ls_core.lsp import Range

    return Range(d.offset_to_line_col(offset1), d.offset_to_line_col(offset2))


def create_text_edit_from_diff(contents: str, new_contents: str) -> List[TextEdit]:
    from difflib import SequenceMatcher
    from robocorp_ls_core.workspace import Document

    d = Document("", contents)

    s = SequenceMatcher(None, contents, new_contents)
    lst = []
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        # print(
        #     "%7s a[%d:%d] (%s) b[%d:%d] (%s)"
        #     % (tag, i1, i2, contents[i1:i2], j1, j2, new_contents[j1:j2])
        # )

        if tag in ("replace", "insert"):
            lst.append(TextEdit(_create_range(d, i1, i2), new_contents[j1:j2]))

        elif tag == "delete":
            lst.append(TextEdit(_create_range(d, i1, i2), ""))

        elif tag == "equal":
            pass

        else:
            raise AssertionError("Unhandled: %s" % (tag,))

    return lst
